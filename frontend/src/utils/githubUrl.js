/**
 * Parse and validate a GitHub repository URL.
 *
 * @param {string} input - Raw user input (URL, partial URL, etc.)
 * @returns {{ ok: true, owner: string, repo: string, url: string }
 *         | { ok: false, error: string }}
 */
export function parseGithubUrl(input) {
  const trimmed = (input ?? "").trim();

  if (trimmed === "") {
    return { ok: false, error: "Enter a GitHub repository URL." };
  }

  // ── Normalise into something URL-parseable ──────────────────────
  let withProtocol = trimmed;

  // If there's no protocol at all, prepend https://
  if (!/^https?:\/\//i.test(withProtocol)) {
    // Must at least look like a host path (contains a dot before the first slash)
    const firstSlash = withProtocol.indexOf("/");
    const segment = firstSlash === -1 ? withProtocol : withProtocol.slice(0, firstSlash);
    if (!segment.includes(".")) {
      return {
        ok: false,
        error:
          "That doesn't look like a link. Example: https://github.com/owner/repo",
      };
    }
    withProtocol = `https://${withProtocol}`;
  }

  // ── Parse ───────────────────────────────────────────────────────
  let parsed;
  try {
    parsed = new URL(withProtocol);
  } catch {
    return {
      ok: false,
      error:
        "That doesn't look like a link. Example: https://github.com/owner/repo",
    };
  }

  // ── Host check ──────────────────────────────────────────────────
  const host = parsed.hostname.replace(/^www\./i, "").toLowerCase();
  if (host !== "github.com") {
    return { ok: false, error: "Only GitHub repositories are supported." };
  }

  // ── Extract path segments ───────────────────────────────────────
  // Remove leading/trailing slashes then split
  const pathSegments = parsed.pathname
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter(Boolean);

  if (pathSegments.length === 0) {
    return {
      ok: false,
      error:
        "That doesn't look like a link. Example: https://github.com/owner/repo",
    };
  }

  if (pathSegments.length === 1) {
    return {
      ok: false,
      error:
        "Add the repository name, like https://github.com/owner/repo",
    };
  }

  // We only care about the first two segments (owner/repo).
  // Everything after (e.g. /tree/main/packages, /pull/3) is stripped.
  const owner = pathSegments[0];
  let repo = pathSegments[1];

  // Strip optional .git suffix from repo
  if (repo.endsWith(".git")) {
    repo = repo.slice(0, -4);
  }

  // ── Validate owner ─────────────────────────────────────────────
  // 1-39 chars, letters/digits/hyphens, cannot start or end with hyphen
  const ownerRe = /^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,37}[a-zA-Z0-9])?$/;
  if (!ownerRe.test(owner)) {
    return {
      ok: false,
      error: "The owner or repository name contains invalid characters.",
    };
  }

  // ── Validate repo ──────────────────────────────────────────────
  // 1-100 chars, letters/digits/dots/hyphens/underscores, not "." or ".."
  if (repo === "." || repo === "..") {
    return {
      ok: false,
      error: "The owner or repository name contains invalid characters.",
    };
  }
  const repoRe = /^[a-zA-Z0-9._-]{1,100}$/;
  if (!repoRe.test(repo)) {
    return {
      ok: false,
      error: "The owner or repository name contains invalid characters.",
    };
  }

  return {
    ok: true,
    owner,
    repo,
    url: `https://github.com/${owner}/${repo}`,
  };
}
