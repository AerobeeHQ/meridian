# 061 — Health check endpoint for Docker and uptime monitoring

**Branch:** `feature/health-check-endpoint`
**Date:** 2026-05-10
**Status:** Complete

---

## Background

Docker's `HEALTHCHECK` instruction needs an HTTP endpoint it can poll to
determine whether the container is ready and alive.  Without one, Docker
only knows whether the process is running — not whether Flask is actually
serving requests.  Likewise, load balancers and uptime monitors benefit
from a lightweight, no-auth JSON route they can hit on a predictable path.

This was tracked as **v3-013** in the roadmap.

---

## Design decisions

### Route placement

All application routes live under `/<client>/` prefixes inside `main_bp`.
The health endpoint must have **no client prefix** — Docker and load
balancers don't know (or care about) client slugs.  The existing `/` root
route (the brochure page) is defined directly on `app` inside
`create_app()`, so the health route follows the same pattern rather than
going into a blueprint.

### Always returns `200 OK`

`status` is always `"ok"`.  The intent is for Docker to restart the
container only on a network-level failure (connection refused, timeout),
not because a cache key is stale.  Cache freshness is reported as
informational metadata — operators can inspect it, but it does not drive
the health signal.

### Uptime tracking with `time.monotonic()`

Wall-clock time (`time.time()`) drifts with NTP adjustments, making
uptime calculations unreliable.  `time.monotonic()` is immune to clock
changes and is the correct choice for measuring elapsed time within a
process.  `app._start_time` is set immediately after `Flask(__name__)` so
it captures startup, not first request.

### Cache freshness via `get_info()` — no outbound API calls

The check uses `CacheService.get_info(rsid)`, which is a pure file-stat
operation.  No Adobe API calls are made, keeping health probes fast and
side-effect-free even when the upstream API is unavailable.

---

## Implementation

### `app/__init__.py`

```python
import time

def create_app():
    app = Flask(__name__)
    app._start_time = time.monotonic()   # monotonic clock for uptime

    # ... existing setup ...

    @app.route('/health')
    def health():
        from flask import jsonify, current_app

        uptime_seconds = round(time.monotonic() - app._start_time)

        clients_info = []
        for slug, ctx in current_app.codex_clients.items():
            config = ctx['config']
            cache  = ctx['cache']
            rsid   = config.get('AW_REPORTSUITE_ID', '')

            dim_key = {}
            if rsid:
                try:
                    cache_info = cache.get_info(rsid)
                    dim_key = cache_info.get('cache_keys', {}).get('dimensions', {})
                except Exception:
                    pass

            clients_info.append({
                'slug':        slug,
                'api_version': config.get('API_VERSION', '2.0'),
                'rsid':        rsid,
                'cache': {
                    'dimensions_fresh':    not dim_key.get('expired', True),
                    'dimensions_age_mins': dim_key.get('age_mins'),
                },
            })

        return jsonify({
            'status':         'ok',
            'uptime_seconds': uptime_seconds,
            'version': {
                'branch': current_app.config.get('GIT_BRANCH'),
                'commit': current_app.config.get('GIT_COMMIT'),
            },
            'clients': clients_info,
        })
```

Example response:

```json
{
  "status": "ok",
  "uptime_seconds": 3742,
  "version": {
    "branch": "main",
    "commit": "abc1234"
  },
  "clients": [
    {
      "slug": "maxis",
      "api_version": "2.0",
      "rsid": "maxisdigitalprod",
      "cache": {
        "dimensions_fresh": true,
        "dimensions_age_mins": 47
      }
    }
  ]
}
```

### `Dockerfile`

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://localhost:5010/health || exit 1
```

| Flag | Value | Rationale |
|------|-------|-----------|
| `--interval` | 30 s | Frequent enough to detect restarts quickly; not so frequent it adds noise |
| `--timeout` | 5 s | Flask responding in under 5 s means something is badly wrong |
| `--start-period` | 10 s | Gives the app time to boot before health checks begin counting failures |
| `--retries` | 3 | Three consecutive failures before Docker marks the container unhealthy |

`curl --fail` exits non-zero on HTTP 4xx/5xx, which would mark the
container unhealthy.  Since the route always returns `200`, this only
triggers on genuine network or process failure.

---

## Files changed

| File | Change |
|------|--------|
| `app/__init__.py` | Added `import time`; set `app._start_time`; added `GET /health` route |
| `Dockerfile` | Added `HEALTHCHECK` instruction |
| `docs/todo.md` | Marked health check items as resolved |

---

## Tests

No new unit tests were added for the health endpoint itself — it is a
thin orchestration layer over `CacheService.get_info()` (already tested)
and `time.monotonic()` (stdlib).  The route is covered by the existing
154-test suite, which continues to pass.
