#!/usr/bin/env python3
"""scribe MCP server.

Captures Claude session notes (with attached media) into one or more
git-versioned notes repos. Configured per-user via a JSON config file at
`~/.config/scribe/config.json`. Supports multiple repos with per-repo user
slugs; one is the `current` default.

Tools exposed:

    save_session(folder, slug, frontmatter, body, media?, commit_message?, repo?)
    repo_info(repo?)
    verify_credentials(repo?)
    add_repo(name, path, user)
    list_repos()
    switch_repo(name)
    remove_repo(name)

A "repo" is identified by its short name (set when added). `path` is the
absolute filesystem path to the cloned notes repo. `user` is the
stakeholder slug — notes go under `<repo>/<user>/...`.

This server runs as the user (host-side, outside any Cowork sandbox), so
it has full filesystem access and the user's git credentials.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


# --- Config location & schema -----------------------------------------------

CONFIG_VERSION = 1


def _config_dir() -> Path:
    """Resolve scribe's config directory, respecting XDG_CONFIG_HOME."""
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base) / "scribe"
    return Path.home() / ".config" / "scribe"


def _config_path() -> Path:
    return _config_dir() / "config.json"


def _empty_config() -> dict:
    return {"version": CONFIG_VERSION, "current": None, "repos": {}}


def _load_config() -> dict:
    """Load config; create an empty one if missing. Migrates older versions in-place."""
    path = _config_path()
    if not path.is_file():
        return _empty_config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RuntimeError(f"scribe config at {path} is not valid JSON: {e}") from e
    # Defensive: ensure expected keys exist.
    data.setdefault("version", CONFIG_VERSION)
    data.setdefault("current", None)
    data.setdefault("repos", {})
    return data


def _save_config(cfg: dict) -> None:
    """Atomically write the config to disk, creating its directory if needed."""
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


# --- Helpers ----------------------------------------------------------------

VALID_REPO_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def _slugify(text: str) -> str:
    """Slugify for filenames: lowercase, hyphens, alnum only."""
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "note"


def _slugify_user_name(name: str) -> str:
    """Match the slug rule used to derive default users from git config user.name."""
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return s.replace("-", "")


def _yaml_value(v: Any) -> str:
    """Render a Python value as a YAML scalar / flow sequence."""
    if v is None:
        return '""'
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(_yaml_value(x) for x in v) + "]"
    s = str(v)
    if any(c in s for c in ":#[]{}&*!|>%@`,") or s.strip() != s:
        return '"' + s.replace('"', '\\"') + '"'
    return s


def _build_frontmatter(fm: dict, media_rel: list[str]) -> str:
    lines = ["---"]
    for k, v in fm.items():
        if v is None or v == "":
            continue
        lines.append(f"{k}: {_yaml_value(v)}")
    if media_rel:
        lines.append(f"media: {_yaml_value(media_rel)}")
    lines.append("---")
    return "\n".join(lines)


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        capture_output=True,
        text=True,
    )


def _resolve_repo(repo_name: str | None) -> tuple[str, dict]:
    """Resolve a repo name (or None for current) to (name, entry).

    Raises ValueError with a helpful message if the requested repo doesn't
    exist or no current is set.
    """
    cfg = _load_config()
    repos = cfg.get("repos", {})
    if repo_name is None:
        current = cfg.get("current")
        if not current:
            raise ValueError(
                "No current scribe repo set. Use `add_repo` to register one, "
                "or pass an explicit `repo` argument."
            )
        if current not in repos:
            raise ValueError(
                f"Current repo {current!r} is not in the configured repos. "
                "Use `list_repos` to see available, or `switch_repo` to fix.",
            )
        return current, repos[current]
    if repo_name not in repos:
        names = ", ".join(sorted(repos.keys())) or "(none)"
        raise ValueError(
            f"Unknown repo {repo_name!r}. Configured repos: {names}.",
        )
    return repo_name, repos[repo_name]


def _commit_and_push(repo: Path, paths: list[str], message: str) -> dict:
    """Pull --rebase, stage, commit, push. Return a structured status."""
    result: dict = {"pulled": False, "committed": False, "pushed": False, "sha": None, "error": None}
    try:
        pull = _git(repo, "pull", "--rebase", "--autostash", check=False)
        if pull.returncode != 0:
            result["error"] = f"pull --rebase failed:\n{pull.stderr or pull.stdout}"
            return result
        result["pulled"] = True

        _git(repo, "add", "--", *paths)

        commit = _git(repo, "commit", "-m", message, check=False)
        if commit.returncode != 0:
            stderr = commit.stderr or commit.stdout
            if "nothing to commit" in stderr.lower():
                result["error"] = "nothing to commit"
                return result
            result["error"] = f"commit failed:\n{stderr}"
            return result
        result["committed"] = True
        result["sha"] = _git(repo, "rev-parse", "HEAD").stdout.strip()

        push = _git(repo, "push", check=False)
        if push.returncode != 0:
            result["error"] = f"push failed (commit kept locally):\n{push.stderr or push.stdout}"
            return result
        result["pushed"] = True
        return result
    except Exception as e:  # noqa: BLE001
        result["error"] = f"git error: {e}"
        return result


def _append_rollup(user_root: Path, date: str, slug: str, transaction: str | None, note_path: Path) -> Path:
    rollup_dir = user_root / "communications"
    rollup_dir.mkdir(parents=True, exist_ok=True)
    rollup_path = rollup_dir / f"{date}-rollup.md"
    if not rollup_path.exists():
        rollup_path.write_text(f"# {date}\n\n")
    rel = os.path.relpath(note_path, rollup_path.parent)
    timestamp = datetime.now().strftime("%H:%M")
    line = f"- {timestamp} — [{slug}]({rel}) — {transaction or '—'}\n"
    with rollup_path.open("a", encoding="utf-8") as f:
        f.write(line)
    return rollup_path


INDEX_SECTIONS = ["clients", "contacts", "workflows", "communications", "monday", "shared"]


def _update_index(user_root: Path, user: str, date: str, slug: str, section: str, transaction: str | None, note_path: Path) -> Path:
    """Add a line under the right section in INDEX.md, reverse-chronological."""
    index_path = user_root / "INDEX.md"
    if not index_path.exists():
        user_root.mkdir(parents=True, exist_ok=True)
        body = [f"# {user} — Notes Index\n"]
        for s in INDEX_SECTIONS:
            body.append(f"\n## {s.capitalize()}\n")
        index_path.write_text("".join(body))

    rel = os.path.relpath(note_path, index_path.parent)
    new_line = f"- {date} — [{slug}]({rel}) — {transaction or '—'}\n"

    text = index_path.read_text(encoding="utf-8")
    section_header = f"## {section.capitalize()}"

    if section_header not in text:
        text = text.rstrip() + f"\n\n{section_header}\n\n"

    lines = text.splitlines(keepends=True)
    out: list[str] = []
    inserted = False
    i = 0
    while i < len(lines):
        out.append(lines[i])
        if not inserted and lines[i].rstrip() == section_header:
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                out.append(lines[j])
                j += 1
            out.append(new_line)
            inserted = True
            i = j
            continue
        i += 1

    if not inserted:
        out.append(new_line)

    index_path.write_text("".join(out), encoding="utf-8")
    return index_path


# --- MCP server -------------------------------------------------------------

mcp = FastMCP("scribe")


@mcp.tool()
def add_repo(name: str, path: str, user: str | None = None) -> dict:
    """Register a notes repo with scribe. Becomes the `current` repo if none was set.

    Args:
        name: Short identifier for this repo (lowercase, alnum + hyphens).
              How you'll refer to it from other tools, e.g. `save_session(repo="ground-zero")`.
        path: Absolute path to the cloned notes repo on this machine.
        user: Stakeholder slug for your notes within this repo. Defaults to the
              slugified value of `git config user.name` in the repo, falling
              back to the global git config.

    Returns:
        Status dict with the repo entry written and the new `current` value.
    """
    if not VALID_REPO_NAME.match(name):
        raise ValueError(
            f"Invalid repo name {name!r}. Use lowercase letters, digits, and hyphens "
            "(must start with a letter or digit; max 63 chars).",
        )

    repo = Path(path).expanduser().resolve()
    if not repo.is_dir():
        raise FileNotFoundError(f"Repo path does not exist or is not a directory: {repo}")
    if not (repo / ".git").exists():
        raise ValueError(f"{repo} is not a git repo (no .git directory).")

    if not user:
        # Try repo-local git config first, then global.
        local_name = _git(repo, "config", "user.name", check=False).stdout.strip()
        global_name = _git(repo, "config", "--global", "user.name", check=False).stdout.strip()
        candidate = local_name or global_name
        if not candidate:
            raise ValueError(
                "No `user` provided and could not derive one from git config. "
                "Set `git config --global user.name '<First Last>'` or pass `user` explicitly.",
            )
        user = _slugify_user_name(candidate)
        if not user:
            raise ValueError(
                f"Could not slugify git user.name {candidate!r} into a usable user slug. "
                "Pass `user` explicitly.",
            )

    cfg = _load_config()
    cfg["repos"][name] = {
        "path": str(repo),
        "user": user,
        "added_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if cfg.get("current") is None:
        cfg["current"] = name
    _save_config(cfg)

    return {
        "added": name,
        "path": str(repo),
        "user": user,
        "current": cfg["current"],
        "config_path": str(_config_path()),
    }


@mcp.tool()
def list_repos() -> dict:
    """List every notes repo configured for scribe, marking the current default."""
    cfg = _load_config()
    return {
        "current": cfg.get("current"),
        "repos": cfg.get("repos", {}),
        "config_path": str(_config_path()),
    }


@mcp.tool()
def switch_repo(name: str) -> dict:
    """Set `name` as the current default repo for save_session and verify."""
    cfg = _load_config()
    if name not in cfg.get("repos", {}):
        names = ", ".join(sorted(cfg.get("repos", {}).keys())) or "(none)"
        raise ValueError(f"Unknown repo {name!r}. Configured: {names}")
    cfg["current"] = name
    _save_config(cfg)
    return {"current": name}


@mcp.tool()
def remove_repo(name: str) -> dict:
    """Remove a repo from scribe's config. Does NOT delete files on disk."""
    cfg = _load_config()
    if name not in cfg.get("repos", {}):
        raise ValueError(f"Unknown repo {name!r}.")
    del cfg["repos"][name]
    if cfg.get("current") == name:
        # Pick another repo as current if any exist; otherwise None.
        remaining = sorted(cfg["repos"].keys())
        cfg["current"] = remaining[0] if remaining else None
    _save_config(cfg)
    return {"removed": name, "current": cfg["current"]}


@mcp.tool()
def save_session(
    folder: str,
    slug: str,
    frontmatter: dict,
    body: str,
    media: list[dict] | None = None,
    commit_message: str | None = None,
    repo: str | None = None,
) -> dict:
    """Write a session note (with optional media), append a daily rollup,
    update INDEX.md, then git pull --rebase / commit / push.

    Args:
        folder: Destination folder relative to the user's notes root within
            the repo, e.g. "clients/jane-doe" or "shared/prds". Created if missing.
        slug: Short slug for the note filename. Will be slugified.
        frontmatter: YAML frontmatter fields. At minimum should include `date`
            (YYYY-MM-DD); `participants`, `transaction`, `tags` are optional.
        body: Markdown body of the note (everything after frontmatter).
            Standard sections: Summary / Decisions / Next Steps / Source Material.
        media: Optional list of {source_path, descriptor} dicts. source_path
            must be an absolute, host-readable file path (typically a Cowork
            uploads path). descriptor is a short label used in the saved filename.
        commit_message: Optional override for the git commit message.
        repo: Name of the configured repo to write to. Defaults to the current.

    Returns:
        Status dict with note_path, media_paths, rollup_path, index_path,
        and a nested `git` block (`pulled`, `committed`, `pushed`, `sha`, `error`).
    """
    media = media or []
    repo_name, repo_entry = _resolve_repo(repo)
    repo_root = Path(repo_entry["path"]).resolve()
    user = repo_entry["user"]
    user_root = repo_root / user

    # Validate inputs.
    folder = folder.strip("/").strip()
    if not folder:
        raise ValueError("folder is required")
    slug = _slugify(slug)
    if not slug:
        raise ValueError("slug must contain at least one alphanumeric character")

    date = frontmatter.get("date") or datetime.now().strftime("%Y-%m-%d")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError(f"invalid date {date!r}; expected YYYY-MM-DD")
    frontmatter["date"] = date

    transaction = frontmatter.get("transaction") or None

    dest_folder = user_root / folder
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Copy media first so frontmatter can reference filenames.
    media_dir = dest_folder / "media"
    copied_rel: list[str] = []
    copied_abs: list[Path] = []
    if media:
        media_dir.mkdir(exist_ok=True)
        for m in media:
            src = Path(m["source_path"]).expanduser()
            if not src.is_file():
                raise FileNotFoundError(f"media source_path not found: {src}")
            descriptor = _slugify(m.get("descriptor") or src.stem)
            ext = src.suffix
            dst = media_dir / f"{date}-{slug}-{descriptor}{ext}"
            n = 2
            while dst.exists():
                dst = media_dir / f"{date}-{slug}-{descriptor}-{n}{ext}"
                n += 1
            shutil.copy2(src, dst)
            copied_rel.append(f"media/{dst.name}")
            copied_abs.append(dst)

    # Write the note.
    note_path = dest_folder / f"{date}-{slug}.md"
    note_content = _build_frontmatter(frontmatter, copied_rel) + "\n\n" + body.rstrip() + "\n"
    note_path.write_text(note_content, encoding="utf-8")

    rollup_path = _append_rollup(user_root, date, slug, transaction, note_path)
    section = folder.split("/", 1)[0]
    index_path = _update_index(user_root, user, date, slug, section, transaction, note_path)

    paths_to_add = [
        str(note_path.relative_to(repo_root)),
        str(rollup_path.relative_to(repo_root)),
        str(index_path.relative_to(repo_root)),
    ] + [str(p.relative_to(repo_root)) for p in copied_abs]

    if commit_message is None:
        suffix = f" ({transaction})" if transaction else ""
        commit_message = f"note: {slug}{suffix}"

    git_status = _commit_and_push(repo_root, paths_to_add, commit_message)

    return {
        "repo": repo_name,
        "note_path": str(note_path.relative_to(repo_root)),
        "media_paths": [str(p.relative_to(repo_root)) for p in copied_abs],
        "rollup_path": str(rollup_path.relative_to(repo_root)),
        "index_path": str(index_path.relative_to(repo_root)),
        "git": git_status,
    }


@mcp.tool()
def repo_info(repo: str | None = None) -> dict:
    """Return basic info about a configured notes repo. Useful for sanity-checking.

    Args:
        repo: Name of the repo to inspect. Defaults to the current.
    """
    repo_name, entry = _resolve_repo(repo)
    repo_root = Path(entry["path"])
    user = entry["user"]
    user_root = repo_root / user

    head = _git(repo_root, "rev-parse", "HEAD", check=False)
    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    remote = _git(repo_root, "remote", "get-url", "origin", check=False)
    return {
        "repo": repo_name,
        "path": str(repo_root),
        "user": user,
        "user_root": str(user_root),
        "user_root_exists": user_root.exists(),
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "origin": remote.stdout.strip() if remote.returncode == 0 else None,
    }


@mcp.tool()
def verify_credentials(repo: str | None = None) -> dict:
    """Run end-to-end checks on a scribe repo: git identity, push access, etc.

    Args:
        repo: Name of the repo to verify. Defaults to the current.

    Returns:
        Dict with `summary`, `fail_count`, `warn_count`, and `checks` (list
        of {name, status, detail}). Statuses are `ok`, `warn`, `fail`.
    """
    checks: list[dict] = []
    fail_count = 0
    warn_count = 0

    def add(name: str, status: str, detail: str = "") -> None:
        nonlocal fail_count, warn_count
        checks.append({"name": name, "status": status, "detail": detail})
        if status == "fail":
            fail_count += 1
        elif status == "warn":
            warn_count += 1

    # Resolve repo (catches "no current set" / "unknown name").
    try:
        repo_name, entry = _resolve_repo(repo)
        repo_root = Path(entry["path"])
        user = entry["user"]
    except ValueError as e:
        add("config_resolves_repo", "fail", str(e))
        return {"summary": "scribe is not configured. Use add_repo to register a repo.",
                "fail_count": 1, "warn_count": 0, "checks": checks}

    add("config_resolves_repo", "ok", f"using repo {repo_name!r} at {repo_root}")

    # Repo state.
    if (repo_root / ".git").exists():
        add("repo_is_git_repo", "ok", str(repo_root))
    else:
        add("repo_is_git_repo", "fail", f"{repo_root} is not a git repo")

    origin = _git(repo_root, "remote", "get-url", "origin", check=False)
    origin_url = origin.stdout.strip() if origin.returncode == 0 else ""
    if origin_url:
        add("origin_configured", "ok", origin_url)
    else:
        add("origin_configured", "fail", "no `origin` remote configured")

    name = _git(repo_root, "config", "user.name", check=False).stdout.strip()
    email = _git(repo_root, "config", "user.email", check=False).stdout.strip()
    if name and email:
        add("git_identity", "ok", f"{name} <{email}>")
    else:
        add("git_identity", "fail", f"name={name!r} email={email!r}")

    # The notes-user slug is sticky — frozen at add_repo time. We deliberately
    # don't compare it against current git config because users with multiple
    # orgs / per-directory git configs would see a useless warn on every run.

    user_root = repo_root / user
    if user_root.exists():
        add("notes_user_dir_exists", "ok", str(user_root))
    else:
        add(
            "notes_user_dir_exists", "warn",
            f"{user_root} does not exist yet — will be created on first save_session",
        )

    status = _git(repo_root, "status", "--porcelain", check=False)
    if status.returncode == 0:
        if status.stdout.strip() == "":
            add("working_tree_clean", "ok", "no uncommitted changes")
        else:
            dirty = [ln for ln in status.stdout.splitlines() if ln.strip()]
            add(
                "working_tree_clean", "warn",
                f"{len(dirty)} uncommitted change(s) — save_session will autostash before pull",
            )
    else:
        add("working_tree_clean", "fail", status.stderr.strip() or "git status failed")

    branch = _git(repo_root, "rev-parse", "--abbrev-ref", "HEAD", check=False).stdout.strip()
    if branch:
        ahead = _git(repo_root, "rev-list", "--count", f"origin/{branch}..HEAD", check=False)
        if ahead.returncode == 0:
            n = int(ahead.stdout.strip() or "0")
            if n == 0:
                add("branch_in_sync", "ok", f"on {branch}, no unpushed commits")
            else:
                add("branch_in_sync", "warn", f"on {branch}, {n} unpushed commit(s)")
        else:
            add("branch_in_sync", "warn", f"on {branch}, no upstream comparison available")

    # Python runtime.
    py_ver = ".".join(str(x) for x in sys.version_info[:3])
    if sys.version_info >= (3, 10):
        add("python_version", "ok", f"{py_ver} ({sys.executable})")
    else:
        add("python_version", "fail", f"{py_ver} (need >=3.10)")

    try:
        import mcp as _mcp_pkg  # type: ignore  # noqa: F401
        ver = getattr(_mcp_pkg, "__version__", "unknown")
        add("mcp_package_importable", "ok", f"mcp=={ver}")
    except Exception as e:  # noqa: BLE001
        add("mcp_package_importable", "fail", f"could not import mcp: {e}")

    # Network / auth.
    try:
        ls = subprocess.run(
            ["git", "-C", str(repo_root), "ls-remote", "origin", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        if ls.returncode == 0:
            add("origin_reachable", "ok", "ls-remote succeeded")
        else:
            add("origin_reachable", "fail", (ls.stderr or ls.stdout).strip())
    except subprocess.TimeoutExpired:
        add("origin_reachable", "fail", "ls-remote timed out after 15s")

    try:
        push = subprocess.run(
            ["git", "-C", str(repo_root), "push", "--dry-run", "origin", "HEAD"],
            capture_output=True, text=True, timeout=15,
        )
        msg = (push.stderr or push.stdout).strip()
        if push.returncode == 0:
            add("push_access", "ok", msg or "dry-run succeeded")
        elif "permission" in msg.lower() or "403" in msg or "denied" in msg.lower():
            add("push_access", "fail", msg)
        else:
            add("push_access", "warn", msg or f"dry-run returned {push.returncode}")
    except subprocess.TimeoutExpired:
        add("push_access", "fail", "push --dry-run timed out after 15s")

    # Verdict.
    if fail_count:
        summary = (
            f"{fail_count} check(s) failed — save_session will not work end-to-end. "
            "Fix the failing items below before using."
        )
    elif warn_count:
        summary = (
            f"All required checks passed; {warn_count} warning(s) to review. "
            "save_session should work."
        )
    else:
        summary = f"All checks passed for repo {repo_name!r}. scribe is ready to use."

    return {
        "summary": summary,
        "fail_count": fail_count,
        "warn_count": warn_count,
        "checks": checks,
    }


if __name__ == "__main__":
    mcp.run()
