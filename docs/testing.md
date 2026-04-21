# Testing Guide

This document describes the Codex test suite, what each test module covers, and how to run the tests.

---

## Overview

Codex uses **pytest** for automated testing. The suite focuses on the service layer — pure logic and file-I/O code that can be tested without real Adobe API credentials or a running Flask app. All tests are fast (< 1 second total), isolated, and deterministic.

| Metric | Value |
|--------|-------|
| Total tests | 129 |
| Test modules | 6 |
| External dependencies required | None |
| Network calls made | None |

---

## Prerequisites

Install the dev dependencies (adds `pytest` and `pytest-cov`):

```bash
uv sync --group dev
```

If you are not using `uv`, install directly:

```bash
pip install pytest pytest-cov
```

---

## Running the Tests

### Run everything

```bash
uv run pytest
```

Or without `uv`:

```bash
python -m pytest
```

### Run a single test file

```bash
uv run pytest tests/test_cache.py
```

### Run a single test class or function

```bash
# All tests in a class
uv run pytest tests/test_cache.py::TestGetOrSet

# One specific test
uv run pytest tests/test_cache.py::TestGetOrSet::test_calls_fetch_func_on_cache_miss
```

### Run with coverage report

```bash
uv run pytest --cov=app --cov-report=term-missing
```

This shows which lines in `app/` are covered and which are not.

### Run verbosely (default — already set in `pyproject.toml`)

```bash
uv run pytest -v
```

---

## Test Modules

### `tests/test_cache.py` — 30 tests

Tests for `app/services/cache.py` (`CacheService`).

| Group | What is tested |
|-------|----------------|
| `TestGetSet` | `get`, `set`, overwrite, multiple keys, isolated cache names, file creation |
| `TestGetOrSet` | Calls fetch function on miss, skips it on hit, caches the result |
| `TestExpiration` | Unexpired key returned; expired key returns `None`; legacy (top-level) TTL fallback; missing metadata treated as expired; custom `ttl_hours` stored correctly |
| `TestClear` | `clear` removes both cache and metadata files; `clear_key` removes one key without affecting others; `clear_all` wipes every JSON file |
| `TestGetInfo` | Returns correct structure for missing and fresh caches; per-key TTL values included; corrupt metadata handled gracefully |
| `TestResilience` | Corrupt cache file returns `None` on `get`; `set` recovers from a corrupt file |

---

### `tests/test_notes.py` — 35 tests

Tests for `app/services/notes.py` (dimension annotation storage).

| Group | What is tested |
|-------|----------------|
| `TestGetEmptyNote` | All expected fields are present; `squad_owners` defaults to `[]`; each call returns an independent copy |
| `TestNoteCRUD` | `get` returns empty note when file is absent; `set` creates file and adds `updated_at`; round-trip fidelity; schema evolution (missing fields backfilled); corrupt file falls back to empty note; `delete` returns `True`/`False` correctly; dimension types are isolated from each other |
| `TestPathSanitization` | Forward slashes in `rsid` are replaced (no subdirectories created); backslashes replaced; `../..` in dimension ID cannot escape the notes directory |
| `TestTagsCRUD` | `get_tags` falls back to `SQUAD_OPTIONS` when no file; `add_tag` appends, persists, strips whitespace; raises `ValueError` for empty or duplicate names; `delete_tag` removes correctly; raises when tag not found; corrupt `_tags.json` falls back gracefully |
| `TestGenerateExpiryNotes` | Fixed messages for `prop` and `event`; `evar` with/without custom days; `listvar` same as `evar`; unknown type returns empty string |

---

### `tests/test_config_loader.py` — 12 tests

Tests for `app/services/config_loader.py`.

| Group | What is tested |
|-------|----------------|
| `TestGetSecretsDir` | Raises `RuntimeError` when `CODEX_SECRETS_DIR` is unset; raises when the directory does not exist; returns a `Path` when valid |
| `TestLoadClients` | Loads a single valid config; loads multiple configs; result is sorted alphabetically; skips `_`-prefixed reserved files; skips configs missing required keys; skips corrupt JSON files; raises when no valid configs are found; raises when the directory is empty; preserves extra config keys |

---

### `tests/test_git_info.py` — 7 tests

Tests for `app/services/git_info.py`.

| Group | What is tested |
|-------|----------------|
| `TestReadGitInfoFile` | Parses `branch` and `commit` from `git_info.txt`; returns `None` values when the file is absent; handles partial files (branch present but no commit line) |
| `TestGetGitInfo` | Returns dict with `branch`, `commit`, `commit_full` keys; truncates full SHA to 7 characters; falls back to `_read_git_info_file` when subprocess is unavailable; returns all-`None` dict when both sources fail |

---

### `tests/test_adobe_analytics.py` — 31 tests

Tests for `app/services/adobe_analytics.py` (`AdobeAnalyticsService`).

| Group | What is tested |
|-------|----------------|
| `TestGenerateWsseHeader` | Header starts with `UsernameToken`; contains `Username`, `PasswordDigest`, `Nonce`, `Created` fields; `Nonce` and `PasswordDigest` are valid Base64; each call produces a unique `Nonce` |
| `TestDecodeRawResponse` | Correctly decodes gzip-compressed bytes; deflate/zlib bytes; plain UTF-8 JSON; string input; returns `{}` for empty bytes, whitespace, and non-JSON text |
| `TestGetProcessingRules` | Formats single rule; conditions joined with newline; actions joined with newline; else-actions appended after `--- ELSE ---` separator; returns `[]` when response contains a different `rsid`; returns `[]` when response is not a list; rule numbers are sequential |
| `TestEndpointRotation` | Rotates to the next endpoint after a `Timeout`; raises the last exception after all four endpoints fail |
| `TestSimpleApiWrappers` | `get_props`, `get_evars`, `get_evar` (by ID, with `variables/` prefix, not found), `get_success_events` extract the correct nested arrays |

---

### `tests/test_adobe_auth.py` — 14 tests

Tests for `app/services/adobe_auth.py` (`OAuth2Auth`).

| Group | What is tested |
|-------|----------------|
| `TestScopeParsing` | List scopes stored as-is; comma-separated string split and stripped; `None` resolves to built-in defaults |
| `TestIsTokenValid` | `False` when no token; `False` when token set but no expiry; `True` when expiry is in the future; `False` when token has expired |
| `TestClearToken` | Resets `_access_token` and `_token_expires_at` to `None`; `is_token_valid` returns `False` after clearing |
| `TestGetAccessToken` | Calls `_fetch_token` on first call; returns cached token without fetching; re-fetches when token is within the 5-minute buffer; re-fetches when token has already expired |
| `TestFetchToken` | POSTs to the correct Adobe IMS endpoint; payload includes `grant_type`, `client_id`, `client_secret`; returns `(token, expiry)` tuple; raises `HTTPError` on non-2xx response |

---

## What Is Not Tested

The following areas are intentionally out of scope for this initial suite — they require a running app or real credentials:

| Area | Reason |
|------|--------|
| Flask routes (`main.py`, `auth.py`) | Require full app factory and client config |
| `adobe_analytics_v2.py` HTTP methods | All paths require OAuth2 token + discovery endpoint |
| `adobe_launch.py` | Same as above |
| `cache_warmer.py` | Background scheduler tied to the app lifecycle |
| Jinja2 templates | End-to-end concern; better suited to browser-level tests |

These are good candidates for the next testing milestone (integration tests with `pytest-flask` and mocked HTTP responses).

---

## Adding New Tests

1. Create a file `tests/test_<module_name>.py`.
2. Import the module you are testing directly — no Flask app context is needed for service-layer tests.
3. Use `tmp_path` (built-in pytest fixture) for any file I/O, so tests don't leave files behind.
4. Use `monkeypatch` to redirect environment variables or patch module-level names.
5. Use `unittest.mock.patch` to mock external HTTP calls — never make real API requests in tests.

---

*Last updated: 2026-04-21*
