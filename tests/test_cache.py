"""
Tests for CacheService (app/services/cache.py).

Covers:
- get / set / get_or_set
- Per-key and legacy TTL expiration
- clear / clear_key / clear_all
- get_info structure
- Corrupt / missing file resilience
"""
import json
import pytest
from datetime import datetime, timedelta

from app.services.cache import CacheService, CONFIG_TTL_HOURS


@pytest.fixture
def cache(tmp_path):
    """Return a CacheService backed by a temporary directory."""
    return CacheService(cache_dir=str(tmp_path))


# ---------------------------------------------------------------------------
# Basic get / set
# ---------------------------------------------------------------------------

class TestGetSet:
    def test_get_missing_key_returns_none(self, cache):
        assert cache.get("suite1", "props") is None

    def test_set_then_get_returns_value(self, cache):
        cache.set("suite1", "props", [{"id": "prop1"}])
        result = cache.get("suite1", "props")
        assert result == [{"id": "prop1"}]

    def test_set_overwrites_existing_value(self, cache):
        cache.set("suite1", "props", ["old"])
        cache.set("suite1", "props", ["new"])
        assert cache.get("suite1", "props") == ["new"]

    def test_multiple_keys_in_same_cache(self, cache):
        cache.set("suite1", "props", [1, 2])
        cache.set("suite1", "evars", [3, 4])
        assert cache.get("suite1", "props") == [1, 2]
        assert cache.get("suite1", "evars") == [3, 4]

    def test_different_cache_names_are_isolated(self, cache):
        cache.set("suite1", "key", "value_a")
        cache.set("suite2", "key", "value_b")
        assert cache.get("suite1", "key") == "value_a"
        assert cache.get("suite2", "key") == "value_b"

    def test_set_creates_cache_file(self, cache, tmp_path):
        cache.set("suite1", "props", [])
        assert (tmp_path / "suite1.json").exists()

    def test_set_creates_metadata_file(self, cache, tmp_path):
        cache.set("suite1", "props", [])
        assert (tmp_path / "suite1_meta.json").exists()

    def test_none_value_stored_and_returned_as_missing(self, cache):
        # Storing None is valid JSON (null), but get() treats None as a miss
        # so the value should not be cached/returned as a hit.
        cache.set("suite1", "key", None)
        assert cache.get("suite1", "key") is None


# ---------------------------------------------------------------------------
# get_or_set
# ---------------------------------------------------------------------------

class TestGetOrSet:
    def test_calls_fetch_func_on_cache_miss(self, cache):
        called = []

        def fetch():
            called.append(1)
            return {"data": "fresh"}

        result = cache.get_or_set("suite1", "evars", fetch)
        assert result == {"data": "fresh"}
        assert len(called) == 1

    def test_does_not_call_fetch_func_on_cache_hit(self, cache):
        cache.set("suite1", "evars", {"data": "cached"})
        called = []

        def fetch():
            called.append(1)
            return {"data": "fresh"}

        result = cache.get_or_set("suite1", "evars", fetch)
        assert result == {"data": "cached"}
        assert len(called) == 0

    def test_caches_result_of_fetch_func(self, cache):
        cache.get_or_set("suite1", "evars", lambda: [1, 2, 3])
        # Second call should not invoke fetch
        result = cache.get_or_set("suite1", "evars", lambda: [9, 9, 9])
        assert result == [1, 2, 3]


# ---------------------------------------------------------------------------
# TTL / expiration
# ---------------------------------------------------------------------------

class TestExpiration:
    def test_unexpired_key_is_returned(self, cache):
        cache.set("suite1", "key", "value", ttl_hours=1)
        assert cache.get("suite1", "key") == "value"

    def test_expired_key_returns_none(self, cache, tmp_path):
        cache.set("suite1", "key", "value", ttl_hours=1)
        # Manually rewrite metadata so the key appears very old
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        meta["keys"]["key"]["created"] = old_time
        meta["created"] = old_time
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        assert cache.get("suite1", "key") is None

    def test_legacy_metadata_format_respected(self, cache, tmp_path):
        """Keys without per-key metadata fall back to top-level 'created'."""
        cache.set("suite1", "key", "value")
        # Remove the per-key metadata entry to simulate legacy format
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        meta["keys"].pop("key", None)
        # Fresh top-level timestamp — should be considered valid
        meta["created"] = datetime.now().isoformat()
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        assert cache.get("suite1", "key") == "value"

    def test_legacy_metadata_expired(self, cache, tmp_path):
        """Legacy top-level timestamp that is too old → key is expired."""
        cache.set("suite1", "key", "value")
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        meta["keys"].pop("key", None)
        meta["created"] = (datetime.now() - timedelta(hours=2)).isoformat()
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        assert cache.get("suite1", "key") is None

    def test_missing_metadata_means_expired(self, cache, tmp_path):
        cache.set("suite1", "key", "value")
        (tmp_path / "suite1_meta.json").unlink()
        assert cache.get("suite1", "key") is None

    def test_custom_ttl_hours_stored_in_metadata(self, cache, tmp_path):
        cache.set("suite1", "key", "v", ttl_hours=CONFIG_TTL_HOURS)
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["keys"]["key"]["ttl_hours"] == CONFIG_TTL_HOURS


# ---------------------------------------------------------------------------
# clear / clear_key / clear_all
# ---------------------------------------------------------------------------

class TestClear:
    def test_clear_removes_cache_and_metadata_files(self, cache, tmp_path):
        cache.set("suite1", "key", "value")
        cache.clear("suite1")
        assert not (tmp_path / "suite1.json").exists()
        assert not (tmp_path / "suite1_meta.json").exists()

    def test_clear_nonexistent_cache_does_not_raise(self, cache):
        cache.clear("nonexistent")  # should not raise

    def test_clear_key_removes_single_key(self, cache):
        cache.set("suite1", "a", 1)
        cache.set("suite1", "b", 2)
        cache.clear_key("suite1", "a")
        assert cache.get("suite1", "a") is None
        # Key 'b' must still be present
        assert cache.get("suite1", "b") == 2

    def test_clear_key_removes_from_metadata(self, cache, tmp_path):
        cache.set("suite1", "a", 1)
        cache.clear_key("suite1", "a")
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        assert "a" not in meta.get("keys", {})

    def test_clear_key_nonexistent_does_not_raise(self, cache):
        cache.clear_key("nonexistent", "missing_key")

    def test_clear_all_removes_every_json_file(self, cache, tmp_path):
        cache.set("s1", "k", 1)
        cache.set("s2", "k", 2)
        cache.clear_all()
        assert list(tmp_path.glob("*.json")) == []


# ---------------------------------------------------------------------------
# get_info
# ---------------------------------------------------------------------------

class TestGetInfo:
    def test_info_for_missing_cache(self, cache):
        info = cache.get_info("nonexistent")
        assert info["exists"] is False
        assert info["expired"] is True
        assert info["created"] is None

    def test_info_for_fresh_cache(self, cache):
        cache.set("suite1", "key", "v")
        info = cache.get_info("suite1")
        assert info["exists"] is True
        assert info["expired"] is False
        assert info["age_mins"] is not None
        assert info["age_mins"] >= 0
        assert info["size_bytes"] > 0

    def test_info_per_key_entries(self, cache):
        cache.set("suite1", "a", 1, ttl_hours=1)
        cache.set("suite1", "b", 2, ttl_hours=24)
        info = cache.get_info("suite1")
        assert "a" in info["cache_keys"]
        assert "b" in info["cache_keys"]
        assert info["cache_keys"]["b"]["ttl_hours"] == 24

    def test_info_with_corrupt_metadata(self, cache, tmp_path):
        """get_info should not raise even if metadata is corrupt."""
        (tmp_path / "bad_meta.json").write_text("{not valid json}")
        info = cache.get_info("bad")
        assert info["expired"] is True


# ---------------------------------------------------------------------------
# Corrupt / missing file resilience
# ---------------------------------------------------------------------------

class TestResilience:
    def test_get_with_corrupt_cache_file_returns_none(self, cache, tmp_path):
        (tmp_path / "suite1.json").write_text("{not valid json}")
        # Write valid metadata so expiry check passes
        meta = {
            "created": datetime.now().isoformat(),
            "keys": {"key": {"created": datetime.now().isoformat(), "ttl_hours": 1}},
        }
        (tmp_path / "suite1_meta.json").write_text(json.dumps(meta))
        assert cache.get("suite1", "key") is None

    def test_set_over_corrupt_cache_file_succeeds(self, cache, tmp_path):
        (tmp_path / "suite1.json").write_text("{not valid json}")
        cache.set("suite1", "key", "value")
        assert cache.get("suite1", "key") == "value"


# ---------------------------------------------------------------------------
# get_stale
# ---------------------------------------------------------------------------

class TestGetStale:
    def test_returns_value_and_age_for_expired_key(self, cache, tmp_path):
        cache.set("suite1", "key", "value", ttl_hours=1)
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        old_time = (datetime.now() - timedelta(hours=2)).isoformat()
        meta["keys"]["key"]["created"] = old_time
        meta["created"] = old_time
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        value, age = cache.get_stale("suite1", "key")
        assert value == "value"
        assert age is not None
        assert age >= timedelta(hours=2)

    def test_returns_value_with_none_age_when_metadata_missing_or_corrupt(self, cache, tmp_path):
        cache.set("suite1", "key", "value")
        (tmp_path / "suite1_meta.json").unlink()
        value, age = cache.get_stale("suite1", "key")
        assert value == "value"
        assert age is None

        # Corrupt metadata should also keep stale fallback value and no age.
        (tmp_path / "suite1_meta.json").write_text("{not valid json}")
        value, age = cache.get_stale("suite1", "key")
        assert value == "value"
        assert age is None

    def test_uses_legacy_top_level_created_when_key_metadata_missing(self, cache, tmp_path):
        cache.set("suite1", "key", "value")
        meta_path = tmp_path / "suite1_meta.json"
        with open(meta_path) as f:
            meta = json.load(f)
        old_time = (datetime.now() - timedelta(hours=3)).isoformat()
        meta["keys"].pop("key", None)
        meta["created"] = old_time
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        value, age = cache.get_stale("suite1", "key")
        assert value == "value"
        assert age is not None
        assert age >= timedelta(hours=3)
