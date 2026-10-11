import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from pathlib import PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from app.config.settings import settings
from schemas.project import ProjectRecord


class RepositoryCloneError(Exception):
    """A public repository could not be safely prepared for a scan."""


class ProjectRepository:
    """Read-only registry of projects the agent is allowed to inspect."""

    def list_projects(self) -> list[ProjectRecord]:
        path = settings.repository_path
        if path is None:
            return []
        path = path.expanduser().resolve()
        if not path.is_dir():
            return []

        project_id = self._project_id(path)
        return [
            ProjectRecord(
                id=project_id,
                name=path.name or "Python project",
                path=path,
                test_framework="pytest" if self._has_pytest(path) else None,
            )
        ]

    @staticmethod
    def from_github_url(repository_url: str, path: Path | None = None) -> ProjectRecord:
        parsed = urlsplit(repository_url)
        _, repository = parsed.path.strip("/").removesuffix(".git").split("/", 1)
        project_id = f"github-{hashlib.sha256(repository_url.encode()).hexdigest()[:12]}"
        return ProjectRecord(
            id=project_id,
            name=repository,
            path=path or Path("."),
            repository_url=repository_url,
        )

    @staticmethod
    def _workspace_candidates() -> list[Path]:
        candidates = (
            settings.repository_workspace_root.expanduser(),
            Path.cwd() / ".tmp" / "testgap-workspaces",
            Path("/var/tmp/testgap-workspaces"),
            Path("/tmp/testgap-workspaces"),
        )
        roots: list[Path] = []
        for candidate in candidates:
            resolved = candidate.resolve()
            if resolved not in roots:
                roots.append(resolved)
        return roots

    @classmethod
    def get_workspace_root(cls) -> Path:
        """Choose the writable configured/temp volume with the most free space."""
        available: list[tuple[int, Path]] = []
        for candidate in cls._workspace_candidates():
            try:
                candidate.mkdir(parents=True, exist_ok=True)
                # Test actual write permission, not just the mode bits.
                with tempfile.NamedTemporaryFile(prefix=".testgap-probe-", dir=candidate):
                    pass
                available.append((shutil.disk_usage(candidate).free, candidate))
            except OSError:
                continue
        if not available:
            raise RepositoryCloneError("No writable temporary workspace is available for repository cloning.")
        return max(available, key=lambda item: item[0])[1]

    @staticmethod
    def clone_repository(repository_url: str, destination: Path) -> Path:
        """Clone one public GitHub repository with bounded history and disk use."""
        project = ProjectRepository.from_github_url(repository_url)
        owner, repository = urlsplit(repository_url).path.strip("/").removesuffix(".git").split("/", 1)
        metadata_url = f"https://api.github.com/repos/{owner}/{repository}"
        request = Request(
            metadata_url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "testgap-agent"},
        )
        try:
            with urlopen(request, timeout=10) as response:
                metadata = json.loads(response.read())
        except HTTPError as exc:
            if exc.code == 404:
                raise RepositoryCloneError(
                    "GitHub repository was not found or is not public. Public repositories only are supported."
                ) from exc
            raise RepositoryCloneError(f"GitHub metadata request failed with HTTP {exc.code}.") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RepositoryCloneError("Could not check GitHub repository metadata; try again shortly.") from exc

        reported_size_kb = metadata.get("size")
        if not isinstance(reported_size_kb, int) or reported_size_kb < 0:
            raise RepositoryCloneError("GitHub did not return a valid repository size.")
        max_bytes = settings.repository_max_size_mb * 1024 * 1024
        if reported_size_kb * 1024 > max_bytes:
            raise RepositoryCloneError(
                f"Repository exceeds the {settings.repository_max_size_mb} MB scan limit."
            )

        destination = destination.resolve()
        workspace_root = destination.parent.parent.resolve()
        if workspace_root not in ProjectRepository._workspace_candidates():
            raise RepositoryCloneError("Invalid temporary workspace destination.")
        try:
            destination.relative_to(workspace_root)
        except ValueError as exc:
            raise RepositoryCloneError("Invalid temporary workspace destination.") from exc
        workspace_root.mkdir(parents=True, exist_ok=True)
        # GitHub's repository size includes history and may overstate a depth-1,
        # blob-filtered checkout. Keep a modest safety floor, then enforce the
        # actual checkout-size limit after removing .git.
        minimum_free_bytes = max(16 * 1024 * 1024, min(reported_size_kb * 1024 // 8, max_bytes))
        if shutil.disk_usage(workspace_root).free < minimum_free_bytes:
            raise RepositoryCloneError(
                "No writable temporary volume has enough free space for this shallow clone."
            )
        if destination.exists():
            raise RepositoryCloneError("The run workspace already exists.")
        destination.parent.mkdir(parents=True, exist_ok=False)

        env = {
            "PATH": os.environ.get("PATH", os.defpath),
            "HOME": str(workspace_root),
            "LANG": "C.UTF-8",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR"):
            if key in os.environ:
                env[key] = os.environ[key]
        try:
            result = subprocess.run(
                [
                    "git", "-c", "http.followRedirects=initial", "clone", "--depth=1",
                    "--filter=blob:none", "--single-branch", "--no-tags", "--quiet",
                    project.repository_url, str(destination),
                ],
                capture_output=True,
                text=True,
                timeout=settings.repository_clone_timeout_seconds,
                check=False,
                shell=False,
                env=env,
            )
        except subprocess.TimeoutExpired as exc:
            shutil.rmtree(destination, ignore_errors=True)
            raise RepositoryCloneError("Repository clone exceeded the time limit.") from exc
        except OSError as exc:
            shutil.rmtree(destination, ignore_errors=True)
            if isinstance(exc, FileNotFoundError):
                return ProjectRepository._download_public_archive(
                    owner=owner,
                    repository=repository,
                    default_branch=metadata.get("default_branch"),
                    destination=destination,
                    max_bytes=max_bytes,
                    timeout=settings.repository_clone_timeout_seconds,
                )
            raise RepositoryCloneError("Could not start the Git clone process.") from exc

        if result.returncode != 0:
            shutil.rmtree(destination, ignore_errors=True)
            raise RepositoryCloneError(
                "GitHub clone failed. Confirm the repository is public and the URL is correct."
            )

        # The analysis does not use Git history; remove it before walking files
        # or running coverage so the limited temporary volume is reclaimed early.
        shutil.rmtree(destination / ".git", ignore_errors=True)

        actual_bytes = 0
        for current, directories, files in os.walk(destination, followlinks=False):
            directories[:] = [
                name for name in directories
                if name != ".git" and not (Path(current) / name).is_symlink()
            ]
            for name in files:
                file_path = Path(current) / name
                if not file_path.is_symlink():
                    try:
                        actual_bytes += file_path.stat().st_size
                    except OSError:
                        continue
                if actual_bytes > max_bytes:
                    shutil.rmtree(destination, ignore_errors=True)
                    raise RepositoryCloneError(
                        f"Checked-out files exceed the {settings.repository_max_size_mb} MB scan limit."
                    )

        return destination

    @staticmethod
    def _download_public_archive(
        *,
        owner: str,
        repository: str,
        default_branch: object,
        destination: Path,
        max_bytes: int,
        timeout: int,
    ) -> Path:
        """Download a public GitHub source archive when the host has no Git binary."""
        if not isinstance(default_branch, str) or not default_branch:
            raise RepositoryCloneError("Git is unavailable and GitHub did not provide a default branch.")

        archive_url = (
            f"https://api.github.com/repos/{owner}/{repository}/tarball/"
            f"{quote(default_branch, safe='')}"
        )
        request = Request(
            archive_url,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "testgap-agent"},
        )
        destination.mkdir(parents=True, exist_ok=False)
        extracted_bytes = 0
        try:
            with urlopen(request, timeout=timeout) as response:
                with tarfile.open(fileobj=response, mode="r|gz") as archive:
                    for member in archive:
                        # GitHub archives wrap all repository entries in one root directory.
                        parts = PurePosixPath(member.name).parts
                        if len(parts) < 2 or parts[0] in ("", ".", ".."):
                            continue
                        relative = PurePosixPath(*parts[1:])
                        if relative.is_absolute() or any(part in ("", ".", "..") for part in relative.parts):
                            continue
                        target = destination.joinpath(*relative.parts)
                        try:
                            target.resolve().relative_to(destination.resolve())
                        except ValueError:
                            continue

                        if member.isdir():
                            target.mkdir(parents=True, exist_ok=True)
                            continue
                        # Do not recreate links or special files from an untrusted archive.
                        if not member.isfile():
                            continue
                        if member.size < 0 or extracted_bytes + member.size > max_bytes:
                            raise RepositoryCloneError(
                                f"Checked-out files exceed the {settings.repository_max_size_mb} MB scan limit."
                            )
                        target.parent.mkdir(parents=True, exist_ok=True)
                        source = archive.extractfile(member)
                        if source is None:
                            continue
                        with source, target.open("wb") as output:
                            shutil.copyfileobj(source, output, length=1024 * 1024)
                        extracted_bytes += member.size
        except RepositoryCloneError:
            shutil.rmtree(destination, ignore_errors=True)
            raise
        except (HTTPError, URLError, TimeoutError, OSError, tarfile.TarError) as exc:
            shutil.rmtree(destination, ignore_errors=True)
            raise RepositoryCloneError(
                "Git is unavailable and GitHub could not provide a source archive for this public repository."
            ) from exc

        if extracted_bytes == 0:
            shutil.rmtree(destination, ignore_errors=True)
            raise RepositoryCloneError("GitHub returned an empty repository archive.")
        return destination

    def get_project(self, project_id: str) -> ProjectRecord | None:
        return next((project for project in self.list_projects() if project.id == project_id), None)

    @staticmethod
    def _project_id(path: Path) -> str:
        return path.name.lower().replace("_", "-").replace(" ", "-") or "workspace"

    @staticmethod
    def _has_pytest(path: Path) -> bool:
        if (path / "pytest.ini").exists():
            return True
        for config_name in ("pyproject.toml", "setup.cfg", "tox.ini"):
            config = path / config_name
            if config.is_file():
                try:
                    if "pytest" in config.read_text(errors="ignore").lower():
                        return True
                except OSError:
                    continue
        for test_dir_name in ("tests", "test"):
            test_dir = path / test_dir_name
            if test_dir.is_dir():
                for test_file in list(test_dir.glob("test_*.py"))[:50]:
                    try:
                        if "pytest" in test_file.read_text(errors="ignore").lower():
                            return True
                    except OSError:
                        continue
        return False
