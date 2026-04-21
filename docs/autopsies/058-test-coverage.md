# 058 — Test Coverage: Initial Test Suite

**Date:** 2026-04-21
**Status:** Complete

---

## Summary

Added a comprehensive automated test suite to Codex, establishing the testing foundation identified as Priority #2 in the v3 roadmap (autopsy 057). The project previously had zero automated tests and relied exclusively on `verify_setup.py` (integration smoke-check) and manual browser testing.

**Result: 129 passing tests across 5 test modules, 0 failures.**

---

## Problem

The codebase had no automated tests at all, as confirmed by the v3 roadmap and autopsy 057. This created risk for:
- Regressions introduced silently during refactoring
- Validating edge cases (TTL expiry, corrupt files, endpoint rotation, security)
- Onboarding new contributors without a safety net

---

## Approach

Focused on **pure-logic and file-I/O layers** — modules that can be tested without real Adobe API credentials or a running Flask app. These are the highest-value targets for a first suite: fast, deterministic, and zero external dependencies.

All tests use `pytest` with `tmp_path` fixtures and `monkeypatch`/`unittest.mock` for isolation — no real files pollute the repo and no network calls are made.

---

## Changes Made

### `pyproject.toml`
- Added `[dependency-groups] dev` with `pytest>=8.0` and `pytest-cov>=5.0`
- Added `[tool.pytest.ini_options]` with `testpaths = ["tests"]` so `pytest` runs without arguments

### `tests/` (new directory)

| File | Tests | Key coverage areas |
|------|-------|--------------------|
| `test_cache.py` | 30 | get/set/get_or_set, per-key TTL, legacy TTL fallback, clear/clear_key/clear_all, get_info, corrupt file resilience |
| `test_notes.py` | 35 | CRUD (get/set/delete), schema evolution, path sanitization (directory traversal), tags CRUD, generate_expiry_notes for all dimension types |
| `test_config_loader.py` | 12 | get_secrets_dir raises, load_clients with valid/invalid/missing/corrupt configs, underscore-file skipping, alphabetical sort |
| `test_git_info.py` | 7 | _read_git_info_file parsing, get_git_info fallback chain (subprocess → file → None), 7-char commit truncation |
| `test_adobe_analytics.py` | 31 | WSSE header format/Base64 validity/uniqueness, _decode_raw_response (gzip/deflate/plaintext/empty/non-JSON), processing rules formatting, endpoint rotation on Timeout, API wrapper methods |
| `test_adobe_auth.py` | 14 | Scope parsing (list/string/None), is_token_valid, clear_token, get_access_token caching + 5-min buffer refresh, _fetch_token HTTP mock |

### `tests/conftest.py`
- Adds project root to `sys.path` so imports work without a `uv` install

---

## What Is Not Tested (intentional scope)

| Area | Reason |
|------|--------|
| Flask routes (`main.py`, `auth.py`) | Require full app factory + client config; integration-level concern |
| `adobe_analytics_v2.py` HTTP methods | All paths require mocked OAuth + discovery; good next target |
| `adobe_launch.py` | Same as above |
| `cache_warmer.py` (APScheduler) | Background scheduler; requires running app context |
| Jinja2 templates | End-to-end concern; browser/screenshot tests more appropriate |

---

## How to Run

```bash
# With uv (adds pytest as dev dependency)
uv sync --group dev
uv run pytest

# Directly with system Python (pytest must be installed)
python3 -m pytest

# With coverage report
python3 -m pytest --cov=app --cov-report=term-missing
```

---

## Files Created/Changed

| File | Action |
|------|--------|
| `pyproject.toml` | Updated — added dev dependencies + pytest config |
| `tests/__init__.py` | Created |
| `tests/conftest.py` | Created |
| `tests/test_cache.py` | Created (30 tests) |
| `tests/test_notes.py` | Created (35 tests) |
| `tests/test_config_loader.py` | Created (12 tests) |
| `tests/test_git_info.py` | Created (7 tests) |
| `tests/test_adobe_analytics.py` | Created (31 tests) |
| `tests/test_adobe_auth.py` | Created (14 tests) |
| `docs/autopsies/058-test-coverage.md` | Created |
