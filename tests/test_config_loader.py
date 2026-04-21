"""
Tests for config_loader (app/services/config_loader.py).

Covers:
- get_secrets_dir raises when env var missing / directory absent
- load_clients with valid configs
- load_clients skips _reserved files
- load_clients skips files missing required keys
- load_clients raises when no valid configs found
- load_clients returns alphabetically sorted dict
"""
import json
import pytest
from pathlib import Path

from app.services.config_loader import get_secrets_dir, load_clients


# Minimal valid config satisfying REQUIRED_KEYS
VALID_CONFIG = {
    "AW_REPORTSUITE_ID": "myrsid",
    "API_VERSION": "2.0",
    "APP_TITLE": "Test Suite",
}


@pytest.fixture
def secrets_dir(tmp_path):
    """Return a temporary directory and set CODEX_SECRETS_DIR to point at it."""
    return tmp_path


def write_config(directory: Path, filename: str, data: dict):
    """Helper to write a JSON config file."""
    (directory / filename).write_text(json.dumps(data))


# ---------------------------------------------------------------------------
# get_secrets_dir
# ---------------------------------------------------------------------------

class TestGetSecretsDir:
    def test_raises_when_env_var_not_set(self, monkeypatch):
        monkeypatch.delenv("CODEX_SECRETS_DIR", raising=False)
        with pytest.raises(RuntimeError, match="CODEX_SECRETS_DIR"):
            get_secrets_dir()

    def test_raises_when_directory_does_not_exist(self, monkeypatch, tmp_path):
        missing = tmp_path / "nonexistent"
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(missing))
        with pytest.raises(RuntimeError, match="does not exist"):
            get_secrets_dir()

    def test_returns_path_when_valid(self, monkeypatch, tmp_path):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(tmp_path))
        result = get_secrets_dir()
        assert result == tmp_path


# ---------------------------------------------------------------------------
# load_clients
# ---------------------------------------------------------------------------

class TestLoadClients:
    def test_loads_single_valid_config(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        write_config(secrets_dir, "acme.json", VALID_CONFIG)
        clients = load_clients()
        assert "acme" in clients
        assert clients["acme"]["AW_REPORTSUITE_ID"] == "myrsid"

    def test_loads_multiple_configs(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        write_config(secrets_dir, "alpha.json", VALID_CONFIG)
        write_config(secrets_dir, "beta.json", {**VALID_CONFIG, "AW_REPORTSUITE_ID": "rsid2"})
        clients = load_clients()
        assert set(clients.keys()) == {"alpha", "beta"}

    def test_result_is_sorted_alphabetically(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        for name in ("zulu", "alpha", "mike"):
            write_config(secrets_dir, f"{name}.json", VALID_CONFIG)
        keys = list(load_clients().keys())
        assert keys == sorted(keys)

    def test_skips_reserved_underscore_files(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        write_config(secrets_dir, "_settings.json", VALID_CONFIG)
        write_config(secrets_dir, "real.json", VALID_CONFIG)
        clients = load_clients()
        assert "_settings" not in clients
        assert "real" in clients

    def test_skips_config_missing_required_keys(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        # This config is missing API_VERSION
        write_config(secrets_dir, "bad.json", {"APP_TITLE": "Only title"})
        write_config(secrets_dir, "good.json", VALID_CONFIG)
        clients = load_clients()
        assert "bad" not in clients
        assert "good" in clients

    def test_skips_corrupt_json_file(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        (secrets_dir / "corrupt.json").write_text("{invalid json")
        write_config(secrets_dir, "valid.json", VALID_CONFIG)
        clients = load_clients()
        assert "corrupt" not in clients
        assert "valid" in clients

    def test_raises_when_no_valid_configs(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        # Only an underscore-prefixed file — should be skipped
        write_config(secrets_dir, "_only.json", VALID_CONFIG)
        with pytest.raises(RuntimeError, match="No valid client configs"):
            load_clients()

    def test_raises_when_directory_is_empty(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        with pytest.raises(RuntimeError):
            load_clients()

    def test_config_data_preserved_in_output(self, monkeypatch, secrets_dir):
        monkeypatch.setenv("CODEX_SECRETS_DIR", str(secrets_dir))
        config = {**VALID_CONFIG, "EXTRA_KEY": "extra_value"}
        write_config(secrets_dir, "client.json", config)
        clients = load_clients()
        assert clients["client"]["EXTRA_KEY"] == "extra_value"
