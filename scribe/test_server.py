"""Offline regression tests for the scribe MCP server.

Run with:
    python3 -m unittest test_server -v

The tests do not require the `mcp` package to be installed — they stub out
`mcp.server.fastmcp` so server.py can import. They do require `git` on PATH.

Each test sets up a fresh temporary git repo + a fresh scribe config in an
isolated XDG_CONFIG_HOME, so real filesystem and real git commands are
exercised end-to-end. Network operations (push, ls-remote) are mocked.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path


# --- Stub mcp.server.fastmcp so server.py imports without the real dep ------

def _install_mcp_stub() -> None:
    if "mcp.server.fastmcp" in sys.modules:
        return
    fake_mcp = types.ModuleType("mcp")
    fake_server = types.ModuleType("mcp.server")
    fake_fastmcp = types.ModuleType("mcp.server.fastmcp")

    class _StubFastMCP:
        def __init__(self, name: str) -> None:
            self.name = name
            self.tools: list = []

        def tool(self):
            def deco(fn):
                self.tools.append(fn)
                return fn
            return deco

        def run(self) -> None:
            pass

    fake_fastmcp.FastMCP = _StubFastMCP
    sys.modules["mcp"] = fake_mcp
    sys.modules["mcp.server"] = fake_server
    sys.modules["mcp.server.fastmcp"] = fake_fastmcp


_install_mcp_stub()

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


# --- Helpers ----------------------------------------------------------------

def _git_init(path: Path, *, with_origin: bool = False, user_name: str = "Test User") -> None:
    subprocess.run(["git", "init", "-q", "-b", "main", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", user_name], check=True)
    if with_origin:
        subprocess.run(
            ["git", "-C", str(path), "remote", "add", "origin", "git@github.com:test/test.git"],
            check=True,
        )
    (path / "README.md").write_text("seed\n")
    subprocess.run(["git", "-C", str(path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "init"], check=True)


def _load_server(config_dir: Path):
    """Re-import server.py with a fresh XDG_CONFIG_HOME."""
    os.environ["XDG_CONFIG_HOME"] = str(config_dir)
    if "server" in sys.modules:
        del sys.modules["server"]
    import server  # noqa: WPS433
    return server


def _patch_git(server, *, pull_fails: str | None = None, push_fails: str | None = None):
    """Mock the server module's `_git` and subprocess so pull/push behave deterministically."""
    real_git = server._git

    def fake_git(repo, *args, check=True):
        if args and args[0] == "pull":
            if pull_fails:
                return types.SimpleNamespace(returncode=1, stdout="", stderr=pull_fails)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        if args and args[0] == "push":
            if push_fails:
                return types.SimpleNamespace(returncode=1, stdout="", stderr=push_fails)
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        return real_git(repo, *args, check=check)

    server._git = fake_git


def _patch_subprocess_run(server, *, ls_returncode=0, ls_stderr="", push_returncode=0, push_stderr=""):
    """Patch the module-level subprocess.run used by verify_credentials for the network checks."""
    real_run = subprocess.run

    def fake(args, **kwargs):
        if isinstance(args, list) and len(args) >= 4 and args[3] == "ls-remote":
            return types.SimpleNamespace(returncode=ls_returncode, stdout="", stderr=ls_stderr)
        if isinstance(args, list) and "push" in args and "--dry-run" in args:
            return types.SimpleNamespace(returncode=push_returncode, stdout="", stderr=push_stderr)
        return real_run(args, **kwargs)

    server.subprocess.run = fake


# --- Tests ------------------------------------------------------------------

class HelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="scribe-helpers-"))
        cls.config_dir = cls.tmp / "config"
        cls.server = _load_server(cls.config_dir)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_slugify_basic(self):
        self.assertEqual(self.server._slugify("Offer Accepted!"), "offer-accepted")

    def test_slugify_collapses_whitespace(self):
        self.assertEqual(self.server._slugify("  Hello   World  123 "), "hello-world-123")

    def test_slugify_empty_falls_back(self):
        self.assertEqual(self.server._slugify("!!!"), "note")

    def test_slugify_user_name(self):
        self.assertEqual(self.server._slugify_user_name("Alex Smith"), "alexsmith")
        self.assertEqual(self.server._slugify_user_name("Morgan Garcia"), "morgangarcia")

    def test_yaml_value_list(self):
        self.assertEqual(self.server._yaml_value([1, 2, "a b"]), "[1, 2, a b]")

    def test_yaml_value_quoted_when_special(self):
        self.assertEqual(self.server._yaml_value("has: colon"), '"has: colon"')

    def test_yaml_value_none_and_bool(self):
        self.assertEqual(self.server._yaml_value(None), '""')
        self.assertEqual(self.server._yaml_value(True), "true")
        self.assertEqual(self.server._yaml_value(False), "false")


class ConfigManagementTests(unittest.TestCase):
    """Tests for add_repo / list_repos / switch_repo / remove_repo."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="scribe-cfg-"))
        self.config_dir = self.tmp / "config"
        self.repo1 = self.tmp / "repo1"
        _git_init(self.repo1, user_name="Alex Smith")
        self.repo2 = self.tmp / "repo2"
        _git_init(self.repo2, user_name="Alex Smith")
        self.server = _load_server(self.config_dir)

    def tearDown(self):
        if "server" in sys.modules:
            del sys.modules["server"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_initial_list_repos_is_empty(self):
        result = self.server.list_repos()
        self.assertIsNone(result["current"])
        self.assertEqual(result["repos"], {})

    def test_add_first_repo_sets_it_as_current(self):
        result = self.server.add_repo(name="ground-zero", path=str(self.repo1))
        self.assertEqual(result["added"], "ground-zero")
        self.assertEqual(result["user"], "alexsmith")  # derived from git config
        self.assertEqual(result["current"], "ground-zero")

    def test_add_second_repo_does_not_change_current(self):
        self.server.add_repo(name="ground-zero", path=str(self.repo1))
        result = self.server.add_repo(name="other", path=str(self.repo2))
        self.assertEqual(result["current"], "ground-zero")  # unchanged

    def test_switch_repo(self):
        self.server.add_repo(name="ground-zero", path=str(self.repo1))
        self.server.add_repo(name="other", path=str(self.repo2))
        result = self.server.switch_repo("other")
        self.assertEqual(result["current"], "other")
        self.assertEqual(self.server.list_repos()["current"], "other")

    def test_switch_repo_unknown_rejected(self):
        with self.assertRaises(ValueError):
            self.server.switch_repo("nope")

    def test_remove_repo_picks_replacement_current(self):
        self.server.add_repo(name="ground-zero", path=str(self.repo1))
        self.server.add_repo(name="other", path=str(self.repo2))
        result = self.server.remove_repo("ground-zero")
        self.assertEqual(result["current"], "other")  # picked replacement

    def test_remove_last_repo_clears_current(self):
        self.server.add_repo(name="ground-zero", path=str(self.repo1))
        result = self.server.remove_repo("ground-zero")
        self.assertIsNone(result["current"])

    def test_add_repo_invalid_name_rejected(self):
        with self.assertRaises(ValueError):
            self.server.add_repo(name="UPPER", path=str(self.repo1))

    def test_add_repo_invalid_path_rejected(self):
        with self.assertRaises(FileNotFoundError):
            self.server.add_repo(name="x", path=str(self.tmp / "does-not-exist"))

    def test_add_repo_non_git_path_rejected(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        with self.assertRaises(ValueError):
            self.server.add_repo(name="x", path=str(plain))

    def test_add_repo_explicit_user_overrides_default(self):
        result = self.server.add_repo(name="r", path=str(self.repo1), user="customslug")
        self.assertEqual(result["user"], "customslug")


class SaveSessionTests(unittest.TestCase):
    """Integration tests for save_session in a multi-repo configuration."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="scribe-save-"))
        self.config_dir = self.tmp / "config"
        self.repo1 = self.tmp / "repo1"
        _git_init(self.repo1, with_origin=True, user_name="Alex Smith")
        self.repo2 = self.tmp / "repo2"
        _git_init(self.repo2, with_origin=True, user_name="Alex Smith")
        self.server = _load_server(self.config_dir)
        self.server.add_repo(name="primary", path=str(self.repo1))
        _patch_git(self.server, push_fails="no remote configured")

    def tearDown(self):
        if "server" in sys.modules:
            del sys.modules["server"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _make_media(self, name: str = "photo.jpg", payload: bytes = b"\xff\xd8\xff\xe0X") -> Path:
        p = self.tmp / f"{name}"
        p.write_bytes(payload)
        return p

    def test_happy_path_uses_current_repo(self):
        media = self._make_media()
        result = self.server.save_session(
            folder="clients/jane-doe",
            slug="Offer Accepted!",
            frontmatter={
                "date": "2026-05-02",
                "participants": ["Alex", "Jane Doe"],
                "transaction": "123 Main St",
                "tags": ["buyer", "offer"],
            },
            body="## Summary\nGot the offer.\n",
            media=[{"source_path": str(media), "descriptor": "Inspection Photo"}],
        )
        self.assertEqual(result["repo"], "primary")
        self.assertEqual(result["note_path"], "alexsmith/clients/jane-doe/2026-05-02-offer-accepted.md")
        self.assertEqual(
            result["media_paths"],
            ["alexsmith/clients/jane-doe/media/2026-05-02-offer-accepted-inspection-photo.jpg"],
        )
        self.assertTrue(result["git"]["pulled"])
        self.assertTrue(result["git"]["committed"])
        self.assertFalse(result["git"]["pushed"])  # mocked-failing push

        note = (self.repo1 / result["note_path"]).read_text()
        self.assertIn("date: 2026-05-02", note)
        self.assertIn("participants: [Alex, Jane Doe]", note)
        self.assertIn("media: [media/2026-05-02-offer-accepted-inspection-photo.jpg]", note)
        # Note: no `type` field anymore — that was real-estate-specific.
        self.assertNotIn("type:", note)

    def test_explicit_repo_argument_overrides_current(self):
        self.server.add_repo(name="secondary", path=str(self.repo2))
        # Re-patch since the new repo registration didn't trigger our mock setup.
        _patch_git(self.server, push_fails="no remote")
        result = self.server.save_session(
            folder="shared/notes",
            slug="cross-repo",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
            repo="secondary",
        )
        self.assertEqual(result["repo"], "secondary")
        self.assertTrue((self.repo2 / result["note_path"]).exists())
        self.assertFalse((self.repo1 / result["note_path"]).exists())

    def test_save_session_unknown_repo_rejected(self):
        with self.assertRaises(ValueError):
            self.server.save_session(
                folder="shared/notes",
                slug="x",
                frontmatter={"date": "2026-05-02"},
                body="## Summary\n.\n",
                repo="does-not-exist",
            )

    def test_save_session_with_no_current_set_fails(self):
        self.server.remove_repo("primary")
        with self.assertRaises(ValueError):
            self.server.save_session(
                folder="x",
                slug="y",
                frontmatter={"date": "2026-05-02"},
                body="## Summary\n.\n",
            )

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            self.server.save_session(
                folder="clients/jane",
                slug="x",
                frontmatter={"date": "May 2 2026"},
                body="## Summary\n.\n",
            )

    def test_missing_folder_rejected(self):
        with self.assertRaises(ValueError):
            self.server.save_session(
                folder="   ",
                slug="x",
                frontmatter={"date": "2026-05-02"},
                body="## Summary\n.\n",
            )

    def test_missing_media_source_path_rejected(self):
        with self.assertRaises(FileNotFoundError):
            self.server.save_session(
                folder="clients/jane",
                slug="x",
                frontmatter={"date": "2026-05-02"},
                body="## Summary\n.\n",
                media=[{"source_path": "/nonexistent/file.jpg", "descriptor": "p"}],
            )

    def test_pull_conflict_short_circuits_before_commit(self):
        _patch_git(self.server, pull_fails="rebase conflict")
        result = self.server.save_session(
            folder="clients/jane",
            slug="x",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
        )
        self.assertFalse(result["git"]["pulled"])
        self.assertFalse(result["git"]["committed"])
        self.assertIn("rebase conflict", result["git"]["error"])
        self.assertTrue((self.repo1 / result["note_path"]).exists())

    def test_default_commit_message_format(self):
        result = self.server.save_session(
            folder="clients/jane",
            slug="closing-tomorrow",
            frontmatter={"date": "2026-05-02", "transaction": "123 Main St"},
            body="## Summary\n.\n",
        )
        sha = result["git"]["sha"]
        self.assertIsNotNone(sha)
        msg = subprocess.run(
            ["git", "-C", str(self.repo1), "log", "-1", "--pretty=%s", sha],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.assertEqual(msg, "note: closing-tomorrow (123 Main St)")

    def test_second_call_same_day_appends_rollup(self):
        self.server.save_session(
            folder="clients/jane",
            slug="first-note",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
        )
        result = self.server.save_session(
            folder="clients/jane",
            slug="second-note",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
        )
        rollup = (self.repo1 / result["rollup_path"]).read_text()
        rollup_lines = [ln for ln in rollup.splitlines() if ln.startswith("- ")]
        self.assertEqual(len(rollup_lines), 2)
        self.assertEqual(sum(1 for ln in rollup_lines if "[first-note]" in ln), 1)
        self.assertEqual(sum(1 for ln in rollup_lines if "[second-note]" in ln), 1)

    def test_index_routes_entries_to_right_sections(self):
        self.server.save_session(
            folder="clients/jane",
            slug="client-thing",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
        )
        result = self.server.save_session(
            folder="shared/prds",
            slug="shared-thing",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
        )
        index = (self.repo1 / result["index_path"]).read_text()
        clients_section = index.split("## Clients", 1)[1].split("## ", 1)[0]
        shared_section = index.split("## Shared", 1)[1].split("## ", 1)[0] if "## Shared" in index else ""
        self.assertIn("client-thing", clients_section)
        self.assertNotIn("shared-thing", clients_section)
        self.assertIn("shared-thing", shared_section)

    def test_media_collision_gets_numeric_suffix(self):
        m1 = self._make_media("a.jpg", payload=b"AAA")
        m2 = self._make_media("b.jpg", payload=b"BBB")
        result = self.server.save_session(
            folder="clients/jane",
            slug="walkthrough",
            frontmatter={"date": "2026-05-02"},
            body="## Summary\n.\n",
            media=[
                {"source_path": str(m1), "descriptor": "photo"},
                {"source_path": str(m2), "descriptor": "photo"},
            ],
        )
        names = [Path(p).name for p in result["media_paths"]]
        self.assertEqual(names[0], "2026-05-02-walkthrough-photo.jpg")
        self.assertEqual(names[1], "2026-05-02-walkthrough-photo-2.jpg")


class RepoInfoTests(unittest.TestCase):
    def test_returns_metadata_for_current(self):
        tmp = Path(tempfile.mkdtemp(prefix="scribe-info-"))
        try:
            config_dir = tmp / "config"
            repo = tmp / "repo"
            _git_init(repo, user_name="Morgan Garcia")
            server = _load_server(config_dir)
            server.add_repo(name="primary", path=str(repo))
            info = server.repo_info()
            self.assertEqual(info["repo"], "primary")
            self.assertEqual(info["path"], str(repo))
            self.assertEqual(info["user"], "morgangarcia")
            self.assertEqual(info["branch"], "main")
            self.assertFalse(info["user_root_exists"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class VerifyCredentialsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="scribe-verify-"))
        self.config_dir = self.tmp / "config"
        self.repo = self.tmp / "repo"
        _git_init(self.repo, with_origin=True, user_name="Alex Smith")
        self.server = _load_server(self.config_dir)
        self.server.add_repo(name="primary", path=str(self.repo))

    def tearDown(self):
        if "server" in sys.modules:
            del sys.modules["server"]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_repos_configured_fails_clean(self):
        self.server.remove_repo("primary")
        result = self.server.verify_credentials()
        self.assertGreaterEqual(result["fail_count"], 1)
        self.assertIn("not configured", result["summary"])

    def test_happy_path_all_green(self):
        _patch_subprocess_run(self.server)
        result = self.server.verify_credentials()
        statuses = {c["name"]: c["status"] for c in result["checks"]}
        self.assertEqual(statuses["repo_is_git_repo"], "ok")
        self.assertEqual(statuses["origin_configured"], "ok")
        self.assertEqual(statuses["git_identity"], "ok")
        self.assertEqual(statuses["origin_reachable"], "ok")
        self.assertEqual(statuses["push_access"], "ok")
        self.assertEqual(statuses["notes_user_dir_exists"], "warn")  # not created yet
        self.assertEqual(result["fail_count"], 0)

    def test_explicit_repo_arg_resolves(self):
        _patch_subprocess_run(self.server)
        result = self.server.verify_credentials(repo="primary")
        self.assertEqual(result["fail_count"], 0)

    def test_explicit_repo_arg_unknown_fails(self):
        result = self.server.verify_credentials(repo="nope")
        self.assertGreaterEqual(result["fail_count"], 1)

    def test_push_permission_denied_fails(self):
        _patch_subprocess_run(self.server, push_returncode=128, push_stderr="ERROR: Permission denied")
        result = self.server.verify_credentials()
        push = next(c for c in result["checks"] if c["name"] == "push_access")
        self.assertEqual(push["status"], "fail")

    def test_origin_unreachable_fails(self):
        _patch_subprocess_run(self.server, ls_returncode=128, ls_stderr="fatal: Could not resolve hostname")
        result = self.server.verify_credentials()
        origin = next(c for c in result["checks"] if c["name"] == "origin_reachable")
        self.assertEqual(origin["status"], "fail")


if __name__ == "__main__":
    unittest.main()
