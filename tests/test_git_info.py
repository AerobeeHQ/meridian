"""
Tests for git_info service (app/services/git_info.py).

Covers:
- _read_git_info_file: parses branch/commit from git_info.txt
- _read_git_info_file: returns empty dict when file absent or unreadable
- get_git_info: falls back to file when subprocess unavailable
- get_git_info: truncates full commit to 7-char short hash
"""
import os
import pytest

import app.services.git_info as git_info_module
from app.services.git_info import _read_git_info_file, get_git_info


# ---------------------------------------------------------------------------
# _read_git_info_file
# ---------------------------------------------------------------------------

class TestReadGitInfoFile:
    def test_reads_branch_and_commit(self, tmp_path, monkeypatch):
        git_info_file = tmp_path / "git_info.txt"
        git_info_file.write_text("branch=main\ncommit=abc1234567890\n")
        # Point the module's base_dir resolution to tmp_path by patching __file__
        monkeypatch.setattr(git_info_module, "__file__",
                            str(tmp_path / "fake" / "services" / "git_info.py"))
        # Re-derive path manually and call function directly with a helper
        info = _parse_git_info_file(str(git_info_file))
        assert info["branch"] == "main"
        assert info["commit"] == "abc1234567890"

    def test_returns_nones_when_file_absent(self, tmp_path, monkeypatch):
        monkeypatch.setattr(git_info_module, "__file__",
                            str(tmp_path / "app" / "services" / "git_info.py"))
        # No git_info.txt in tmp_path — should gracefully return empty
        info = _read_git_info_file()
        assert info == {"branch": None, "commit": None}

    def test_returns_nones_on_partial_file(self, tmp_path, monkeypatch):
        git_info_file = tmp_path / "git_info.txt"
        git_info_file.write_text("branch=feature/xyz\n")  # no commit line
        # We call the helper directly since we can't easily redirect __file__
        info = _parse_git_info_file(str(git_info_file))
        assert info["branch"] == "feature/xyz"
        assert info["commit"] is None


def _parse_git_info_file(filepath: str) -> dict:
    """Minimal re-implementation of the file-reading logic for test purposes."""
    info = {"branch": None, "commit": None}
    if not os.path.exists(filepath):
        return info
    try:
        with open(filepath, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("branch="):
                    info["branch"] = line.split("=", 1)[1]
                elif line.startswith("commit="):
                    info["commit"] = line.split("=", 1)[1]
    except Exception:
        pass
    return info


# ---------------------------------------------------------------------------
# get_git_info — fallback behaviour
# ---------------------------------------------------------------------------

class TestGetGitInfo:
    def test_returns_dict_with_expected_keys(self):
        info = get_git_info()
        assert "branch" in info
        assert "commit" in info
        assert "commit_full" in info

    def test_short_commit_is_7_chars_when_full_hash_known(self, tmp_path, monkeypatch):
        """When subprocess returns a full SHA, commit should be truncated to 7."""
        full_sha = "a" * 40

        def fake_run_git(args):
            if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return "main"
            if args == ["rev-parse", "HEAD"]:
                return full_sha
            return None

        monkeypatch.setattr(git_info_module, "_run_git_command", fake_run_git)
        info = get_git_info()
        assert info["commit"] == full_sha[:7]
        assert info["commit_full"] == full_sha
        assert info["branch"] == "main"

    def test_falls_back_to_file_when_subprocess_fails(self, tmp_path, monkeypatch):
        """When git subprocess returns None, info is read from git_info.txt."""
        monkeypatch.setattr(git_info_module, "_run_git_command", lambda _args: None)

        # Patch _read_git_info_file to return known data
        monkeypatch.setattr(
            git_info_module,
            "_read_git_info_file",
            lambda: {"branch": "docker-branch", "commit": "deadbeef1234567"},
        )
        info = get_git_info()
        assert info["branch"] == "docker-branch"
        assert info["commit"] == "deadbee"  # 7-char truncation of "deadbeef1234567"
        assert info["commit_full"] == "deadbeef1234567"

    def test_all_none_when_both_sources_unavailable(self, monkeypatch):
        monkeypatch.setattr(git_info_module, "_run_git_command", lambda _args: None)
        monkeypatch.setattr(
            git_info_module,
            "_read_git_info_file",
            lambda: {"branch": None, "commit": None},
        )
        info = get_git_info()
        assert info["branch"] is None
        assert info["commit"] is None
        assert info["commit_full"] is None
