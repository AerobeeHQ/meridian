# Plan: Background Pre-Caching

**Roadmap item:** Download and cache dimension configuration data in the background so it's ready when the user first opens the app. Cache for 1 day. Add a force-refresh button to listing and detail pages.

**Complexity: Medium**

---

## Overview

Currently, Meridian fetches data on first request and caches it for 1 hour. If the cache is cold (e.g. after an hourly expiry), the user waits for API calls on page load. This feature moves that wait off the request path by:

1. Warming the cache in the background at startup and on a 24-hour schedule.
2. Extending the TTL for configuration data (which rarely changes) to 24 hours.
3. Adding a "Force Refresh" button on listing and detail pages for on-demand cache invalidation.

---

## Current Caching Behaviour

- `CacheService` in `cache.py` uses a 1-hour TTL hardcoded in `_is_expired()`.
- Cache is populated lazily (on first request).
- There is no scheduler, background thread, or startup hook.
- Cache can be fully cleared via `/cache/clear`.

---

## Implementation Plan

### Step 1 — Configurable TTL per cache key

Modify `CacheService` to support per-key TTL (in hours):

```python
# cache.py
DEFAULT_TTL_HOURS = 1
CONFIG_TTL_HOURS = 24  # for dimension/event configs that rarely change

def get_or_set(self, cache_name, key, fetch_func, ttl_hours=DEFAULT_TTL_HOURS):
    ...
```

Pass `ttl_hours=24` when caching: `dimensions`, `events`, `processing_rules`, `channel_rules`, `marketing_channels`, `listvars`.

Keep `ttl_hours=1` for trend and top-items data (changes frequently).

### Step 2 — Background cache warmer using APScheduler

Add `APScheduler` to dependencies:

```
uv add apscheduler
```

Create `app/services/cache_warmer.py`:

```python
from apscheduler.schedulers.background import BackgroundScheduler

def warm_cache(app):
    """Fetch and cache all slow-changing configuration data."""
    with app.app_context():
        rsid = app.config['AW_REPORTSUITE_ID']
        service = get_api_service_v2(app)
        # Fetch each config type and store in cache
        cache.get_or_set(rsid, 'dimensions', lambda: service.get_dimensions(rsid), ttl_hours=24)
        cache.get_or_set(rsid, 'events', lambda: service.get_success_events(rsid), ttl_hours=24)
        # ... processing_rules, channel_rules, marketing_channels, listvars

def start_scheduler(app):
    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: warm_cache(app), 'interval', hours=24, id='cache_warmer')
    scheduler.start()
    warm_cache(app)  # Run immediately at startup
    return scheduler
```

Call `start_scheduler(app)` from `run.py` after the Flask app is created.

**Guard against double-start:** In development, Flask's reloader starts the process twice. Use `os.environ.get('WERKZEUG_RUN_MAIN')` to only start the scheduler in the main process.

### Step 3 — Force Refresh button

#### Backend

Add a new route for per-key cache invalidation:

```python
@app.route('/cache/refresh/<cache_key>')
def cache_refresh(cache_key):
    """Clear a specific cache key and re-warm it."""
    rsid = app.config['AW_REPORTSUITE_ID']
    ALLOWED_KEYS = {'dimensions', 'events', 'processing_rules', 'channel_rules', 'marketing_channels', 'listvars'}
    if cache_key not in ALLOWED_KEYS:
        abort(400)
    cache.clear_key(rsid, cache_key)
    warm_cache_key(app, rsid, cache_key)  # Re-fetch immediately
    return redirect(request.referrer or '/')
```

Add `clear_key(cache_name, key)` to `CacheService` to delete a single key rather than the entire cache.

#### Frontend

Add a small "↺ Refresh" button to each listing page and detail page. Clicking it hits `/cache/refresh/<relevant_key>` and redirects back.

In `table.html`, add alongside the CSV export link:
```html
<a href="/cache/refresh/{{ cache_key }}" class="btn btn-sm btn-outline-secondary">↺ Refresh</a>
```

Pass `cache_key` as a template variable from each route.

### Step 4 — Cache status page update

Update `/cache` page to show:
- Last refreshed time per key
- 24-hour TTL for config keys vs 1-hour for report keys
- Whether the warmer has run

---

## Files to Create / Change

| File | Change |
|------|--------|
| `app/services/cache.py` | Add `ttl_hours` parameter; add `clear_key()` method |
| `app/services/cache_warmer.py` | New: warm_cache(), start_scheduler() |
| `app/routes/main.py` | Add `/cache/refresh/<key>` route; pass `cache_key` to listing templates |
| `app/templates/table.html` | Add Force Refresh button |
| `app/templates/detail.html` | Add Force Refresh button |
| `app/templates/event_detail.html` | Add Force Refresh button |
| `app/templates/listvar_detail.html` | Add Force Refresh button |
| `app/templates/cache.html` | Show per-key TTL and last-refreshed info |
| `run.py` | Call `start_scheduler(app)` |
| `pyproject.toml` | Add `apscheduler` dependency |

---

## Risks & Notes

- **Flask reloader:** Must guard scheduler startup to avoid double-run in dev mode.
- **Docker:** Works as-is in a single-container deployment. Multi-container would need a shared cache store (Redis) to avoid each container warming independently — out of scope for now.
- **Startup time:** Warming the cache at startup means the first startup takes longer. Consider warming in a background thread so the app is immediately available.
- **APScheduler is lightweight:** No Redis/Celery infrastructure needed. It runs in the same process as Flask.
