# Autopsy: Merchandising eVar Expiration Display Fix

**Issue:** Fix merchandising eVar expiration display + caching improvements
**Date:** March 25, 2026
**Status:** Completed

## Summary

Fixed eVar expiration and allocation display for merchandising eVars by parsing API 2.0 description metadata rather than relying solely on the deprecated API 1.4. Also introduced centralized cache TTL management, a background cache warmer, and per-key TTL support in the cache service.

## Changes Made

### Files Created
- `app/services/cache_warmer.py` - Background scheduler using APScheduler that warms slow-changing config cache keys at startup and every 24 hours

### Files Modified

1. **`app/services/cache.py`**
   - Added `CONFIG_TTL_HOURS = 24` constant for slow-changing configuration data
   - Added per-key TTL support to `set()` and `get_or_set()` — each cache key tracks its own creation timestamp and TTL in a `_meta.json` sidecar file
   - `get_info()` now reports per-key expiry details
   - Added `clear_key()` to remove a single cache key without nuking the whole cache

2. **`app/services/adobe_analytics_v2.py`**
   - Added `parse_description_metadata(description)` static method that extracts `expiration_type`, `expiration_custom_days`, and `allocation_type` from the structured text Adobe embeds in the API 2.0 description field

3. **`app/routes/main.py`**
   - Updated all `get_cached_data` calls for config data to use `ttl_hours=CONFIG_TTL_HOURS` (24h)
   - Updated `evar_detail` to call `parse_description_metadata` as primary source, falling back to API 1.4 for fields not available in 2.0 (merchandising_syntax, binding_events, enabled)
   - Added `cache_key` to all template contexts to support the Refresh button
   - Added `/cache/refresh/<cache_key>` route to clear and re-warm a specific cache key

4. **`app/__init__.py`**
   - Replaced startup cache-clear with `start_scheduler(app)` — cache is now warmed proactively rather than reset on restart

### Dependencies Added
- `apscheduler` — lightweight background task scheduler

## Bugs Fixed During Code Review

1. **Critical `ImportError` in `evar_detail`**: An inline `from app.services.adobe_analytics_v2 import AdobeAnalyticsV2` referenced a non-existent class name. Fixed to use the already-imported `AdobeAnalyticsV2Service`.

2. **Scheduler double-start guard logic**: The original guard `if is_reloader_active is not None and is_reloader_active != 'true'` was a no-op — it only triggered if `WERKZEUG_RUN_MAIN` was set to something other than `'true'`, which Flask never does. Fixed to `if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true'` which correctly skips the parent/watcher process in dev mode while running in production.

## Design Decisions

- **API 2.0 as primary, 1.4 as fallback**: Adobe is deprecating API 1.4 in August 2026. Parsing the description field is a bridge strategy until 2.0 exposes these fields natively.
- **24h TTL for config data**: eVar/event/channel configuration changes rarely. A 24h TTL reduces API calls without risking stale critical data.
- **Cache warming on startup**: Users no longer see a cold cache after a restart. The warmer runs in a daemon thread so it does not block app startup.

## Limitations / Future Work

- `parse_description_metadata` depends on a specific text format in the API 2.0 description field. If Adobe changes that format, parsing will silently fail and fall back to 1.4.
- The `get_or_set` method cannot cache a legitimate `None` return value (treated as a cache miss). Not currently an issue since API responses are always lists or dicts.
