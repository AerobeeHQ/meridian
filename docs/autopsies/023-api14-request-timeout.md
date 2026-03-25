# 023 — API 1.4 Request Timeout

**Date:** March 25, 2026
**Status:** Completed
**Branch:** `fix/api14-request-timeout`
**Depends on:** `fix/evar-api14-graceful-async-rules` (autopsy 022)

## Problem

Even after autopsy 022 prevented the API 1.4 crash from propagating to the page render, loading `/evars/evar1` while `api.omniture.com` was unreachable still took ~60 seconds before the page appeared. The `evar_config` fetch was running in a `ThreadPoolExecutor` thread, and the thread was blocked for the full OS TCP timeout (~60 s) waiting for a response that never came.

Root cause: `requests.post()` in `AdobeAnalyticsService._make_request()` had no `timeout` parameter. Python's `requests` defaults to no timeout, deferring entirely to the OS TCP stack.

## Fix

### `app/services/adobe_analytics.py`

`AdobeAnalyticsService.__init__()` gains a `request_timeout` parameter (default `5.0` seconds):

```python
def __init__(self, username: str, secret: str, request_timeout: float = 5.0):
    ...
    self.request_timeout = request_timeout
```

`timeout=self.request_timeout` is passed to both `requests.post()` call sites:

- `_make_request()` — primary request path
- `_fetch_with_manual_decoding()` — compression-retry path

### `app/routes/main.py`

`get_api_service_v14()` reads the new config key when constructing the service:

```python
app.codex_api_service_v14 = AdobeAnalyticsService(
    username=current_app.config['AW_USERNAME'],
    secret=current_app.config['AW_SECRET'],
    request_timeout=current_app.config.get('API_V14_TIMEOUT', 5.0),
)
```

The `.get(..., 5.0)` fallback means existing `config.json` files without the new key continue to work with the 5-second default.

### `config.dist.json`

New key with an explanatory comment:

```json
"_comment_api14_timeout": "Timeout in seconds for API 1.4 HTTP requests. ...",
"API_V14_TIMEOUT": 5
```

## Why 5 Seconds, Not 500ms

500ms is achievable in a lab environment but is aggressive for real-world cross-Pacific Adobe API calls. At 500ms, transient network jitter could cause spurious timeouts when the API is healthy, resulting in missing merchandising/allocation data on eVar detail pages. 5 seconds:

- Fails within the browser's perceived "fast" window when the API is truly down
- Survives normal latency variation on the APAC → US west coast path
- Is easily tunable downward via `API_V14_TIMEOUT` in `config.json` if the deployment environment has low-latency access to `api.omniture.com`

## Sequence After This Change

```
Browser requests /evars/evar1
  → ThreadPoolExecutor fires evar_config fetch (API 1.4)
  → API 1.4 unreachable → requests.post() times out after 5 s
  → try/except (autopsy 022) catches the Timeout, sets evar_config = None
  → Page renders in ~5 s with N/A for merchandising/allocation fields
  → Browser fires fetch('/api/related-rules/evar/evar1') asynchronously
```

Previously the same sequence took ~60 seconds.

## Files Changed

| File | Change |
|---|---|
| `app/services/adobe_analytics.py` | `request_timeout` constructor param; `timeout=` on both `requests.post()` calls |
| `app/routes/main.py` | `get_api_service_v14()` passes `API_V14_TIMEOUT` from config |
| `config.dist.json` | New `API_V14_TIMEOUT` key (default `5`) with explanatory comment |

## Testing

1. **API down, normal flow:** With `api.omniture.com` unreachable, load `/evars/evar1`. Verify the page renders in ≤ `API_V14_TIMEOUT + 1` seconds (i.e., ~6 s for default config) rather than ~60 s.
2. **API up, normal flow:** With the API reachable, verify the eVar detail page loads normally with merchandising/allocation data populated.
3. **Configurable timeout:** Set `API_V14_TIMEOUT` to `1` in `config.json`, restart the app, and confirm the page renders in ~2 s when the API is unreachable.
