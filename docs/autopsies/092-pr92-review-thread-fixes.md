# 092 — PR #92 Review Thread Fixes

**Date:** 2026-05-22
**Branch:** `fix/api14-endpoint-discovery-and-timeout`
**Status:** Complete

---

## Problem

PR #92 received follow-up review feedback on stale-cache fallback behavior, accessibility attributes in warning banners, and missing unit test coverage for new cache functionality.

---

## Solution

- Marked warning-banner SVG icons in `listing.html` and `detail.html` as decorative with `aria-hidden="true"` and `focusable="false"`.
- Updated `CacheService.get_stale()` to fall back to legacy top-level metadata (`created`) when per-key metadata is missing.
- Tightened stale-fallback exception handling in `get_cached_data()` to only catch `requests.exceptions.RequestException`.
- Improved stale age formatting precision by keeping hour-level output up to 48 hours.
- Added `TestGetStale` unit tests to cover:
  - stale return with age for expired keys,
  - missing/corrupt metadata behavior,
  - legacy metadata fallback age calculation.

---

## Files Changed

- `app/templates/listing.html`
- `app/templates/detail.html`
- `app/services/cache.py`
- `app/routes/main.py`
- `tests/test_cache.py`
- `docs/autopsies/092-pr92-review-thread-fixes.md`

---

## Validation

- Targeted: `pytest tests/test_cache.py` → **32 passed**
- Full suite: `pytest` → **169 passed**
- CodeQL: 1 pre-existing alert in `tests/test_adobe_analytics.py` (`py/incomplete-url-substring-sanitization`), not introduced by this change.
