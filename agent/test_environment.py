"""Prepare an isolated Python runtime for public-repository test execution."""

import hashlib
import logging
import os
import re
import shutil
import subprocess
import sys
import venv
from pathlib import Path


class TestEnvironmentError(RuntimeError):
    """A target repository's test environment could not be prepared safely."""

    __test__ = False


logger = logging.getLogger(__name__)


_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_IGNORED_REQUIREMENT_PREFIXES = ("-", ".", "/", "\\")


def _requirements(root: Path) -> tuple[Path | None, str]:
    manifest = root / "requirements.txt"
    if not manifest.is_file():
        return None, ""
    try:
        text = manifest.read_text(errors="strict")
    except (OSError, UnicodeError) as exc:
        raise TestEnvironmentError("Could not read requirements.txt.") from exc
    if len(text) > 64_000:
        raise TestEnvironmentError("requirements.txt exceeds the 64 KB setup limit.")
    for line in text.splitlines():
        requirement = line.split("#", 1)[0].strip()
        if not requirement:
            continue
        if (
            requirement.startswith(_IGNORED_REQUIREMENT_PREFIXES)
            or "://" in requirement
            or " @ " in requirement
        ):
            raise TestEnvironmentError(
                "requirements.txt contains a direct URL, local path, or pip option; automatic setup skipped."
            )
    return manifest, hashlib.sha256(text.encode()).hexdigest()


def _python_path(environment_root: Path) -> Path:
    if os.name == "nt":
        return environment_root / "Scripts" / "python.exe"
    return environment_root / "bin" / "python"


def _subprocess_environment(
    home: Path,
    python_path: Path | None = None,
    *,
    allow_network: bool = False,
) -> dict[str, str]:
    path_parts = []
    if python_path is not None:
        path_parts.append(str(python_path.parent))
    path_parts.append(os.environ.get("PATH", os.defpath))
    env = {
        "PATH": os.pathsep.join(path_parts),
        "HOME": str(home),
        "TMPDIR": str(home),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
    }
    if "SYSTEMROOT" in os.environ:
        env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
    if allow_network:
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR"):
            if key in os.environ:
                env[key] = os.environ[key]
    return env


def _example_settings(root: Path) -> dict[str, str]:
    """Read names only from a checked-in example; never load real .env values."""
    example = next(
        (root / name for name in (".env.example", ".env.sample", ".env.template") if (root / name).is_file()),
        None,
    )
    if example is None:
        return {}
    try:
        lines = example.read_text(errors="replace").splitlines()[:500]
    except OSError:
        return {}

    env: dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, _ = stripped.partition("=")
        key = key.removeprefix("export ").strip()
        if not separator or not _ENV_KEY.fullmatch(key):
            continue
        upper_key = key.upper()
        if upper_key == "DATABASE_URL":
            env[key] = "postgresql+asyncpg://testgap:testgap@127.0.0.1:5432/testgap"
        elif upper_key.endswith(("_URL", "_URI")):
            env[key] = "http://127.0.0.1"
        elif any(token in upper_key for token in ("SECRET", "_KEY", "TOKEN", "PASSWORD")):
            env[key] = "testgap-placeholder-not-a-real-secret"
        elif upper_key.endswith("_PORT"):
            env[key] = "5432"
        elif upper_key.endswith(("_TIMEOUT", "_SECONDS", "_INTERVAL")):
            # Keep dummy settings parseable by projects that expect integers.
            env[key] = "90"
        elif upper_key.endswith(("_SIZE_MB", "_MAX_SIZE_MB")):
            env[key] = "200"
        elif upper_key.endswith(("_LIMIT", "_COUNT", "_RETRIES", "_WORKERS")):
            env[key] = "1"
        else:
            env[key] = "testgap-placeholder"
    return env


def dependency_setup_timeout(timeout_seconds: int) -> int:
    """Return the bounded timeout used when installing repository dependencies."""
    return max(300, min(timeout_seconds, 600))


def prepare_test_environment(
    root: Path,
    *,
    timeout_seconds: int,
) -> tuple[Path, dict[str, str], dict[str, str]]:
    """Install safe, manifest-declared dependencies in a disposable per-run venv."""
    manifest, fingerprint = _requirements(root)
    env_root = root.parent / ".testgap-venv"
    runner = _python_path(env_root)
    marker = env_root / ".testgap-requirements-sha256"
    if manifest is None:
        return Path(sys.executable), fallback_test_environment(root, root.parent), {
            "status": "no_requirements_manifest"
        }

    try:
        if not runner.is_file() or not marker.is_file() or marker.read_text() != fingerprint:
            if env_root.exists():
                shutil.rmtree(env_root)
            # Clone workspaces may be mounted `noexec` by hosted runtimes.
            # On POSIX, symlink the host interpreter instead of copying it
            # into that mount; otherwise ensurepip cannot launch the venv Python.
            venv.EnvBuilder(
                with_pip=True,
                clear=True,
                symlinks=(os.name != "nt"),
            ).create(env_root)
            # Keep first-run dependency setup bounded even if the deployment's
            # general scan timeout is configured much higher.
            setup_timeout = dependency_setup_timeout(timeout_seconds)
            install = subprocess.run(
                [
                    str(runner), "-m", "pip", "install", "--disable-pip-version-check",
                    "--no-input", "--no-cache-dir", "--only-binary=:all:",
                    "-r", str(manifest), "pytest", "pytest-asyncio", "coverage",
                ],
                cwd=root,
                capture_output=True,
                text=True,
                timeout=setup_timeout,
                check=False,
                shell=False,
                env=_subprocess_environment(env_root, runner, allow_network=True),
            )
            if install.returncode != 0:
                raise TestEnvironmentError(
                    f"Could not install the repository's test dependencies (pip exit code {install.returncode})."
                )
            marker.write_text(fingerprint)
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(env_root, ignore_errors=True)
        raise TestEnvironmentError("Installing repository test dependencies exceeded the setup time limit.") from exc
    except (OSError, subprocess.CalledProcessError) as exc:
        shutil.rmtree(env_root, ignore_errors=True)
        logger.exception("Could not create the disposable Python test environment")
        raise TestEnvironmentError("Could not create the disposable Python test environment.") from exc

    child_env = _subprocess_environment(env_root, runner)
    child_env["PYTHONPATH"] = os.pathsep.join((str(root), str(root / "src")))
    child_env.update(_example_settings(root))
    return runner, child_env, {"status": "ready", "dependency_manifest": "requirements.txt"}


def fallback_test_environment(root: Path, home: Path) -> dict[str, str]:
    """Build a scrubbed process environment with local-only example settings."""
    env = _subprocess_environment(home)
    env["PYTHONPATH"] = os.pathsep.join((str(root), str(root / "src")))
    env.update(_example_settings(root))
    return env
