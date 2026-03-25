# 024 — API 1.4 Friendly Error Pages

**Date:** March 25, 2026
**Status:** Completed
**Branch:** `fix/api14-error-pages`
**Depends on:** `fix/api14-request-timeout` (autopsy 023)

## Problem

With the timeout fix from autopsy 023, API 1.4 failures now surface quickly (~5 s) rather than after a 60-second hang. However, the unhandled `requests.exceptions.ReadTimeout` (and other `RequestException` variants) still propagated to Flask's default error handler, producing the Werkzeug debugger in development mode or a bare 500 page in production.

Affected routes (all use API 1.4 synchronously):

| Route | Function |
|---|---|
| `/listvars` | `listvars()` |
| `/listvars/<name>` | `listvar_detail()` |
| `/processing-rules` | `processing_rules()` |
| `/marketing-channels` | `marketing_channels()` |
| `/channel-rules` | `channel_rules()` |
| Export variants of the above | — |

The `evar_detail` ThreadPoolExecutor path already had its own try/except (autopsy 022), so it was not affected.

## Fix

### `app/templates/_api_error.html` (new)

A Jinja2 template extending `base.html` that renders a friendly, on-brand error page. Key elements:

- Bootstrap `border-danger` card with a warning icon in the header
- Plain-language message explaining what happened and pointing to the Cache page for manual recovery
- "Try again" button that reloads `{{ request.url }}`, and a "Home" link
- HTML5 `<details>/<summary>` collapsible section containing the exception type, message, and full formatted traceback in a scrollable `<pre>` block — visible to developers without cluttering the default view

No JavaScript is required for the collapsible section; `<details>` is supported in all modern browsers.

### `app/routes/main.py`

Two additions:

**`_render_api_error(exc, status=503)`** — a helper that calls `render_template('_api_error.html', ...)` with all required base-template variables (those not injected by the context processor: `rsid`, `cache_info`, `active_tab`, `dimension_id`) plus the error details extracted from the exception and the current traceback.

**`@main_bp.app_errorhandler(requests.exceptions.RequestException)`** — registers the handler on the application (not just the blueprint) so it fires for all routes. Logs the error at WARNING level and delegates to `_render_api_error`.

Also added `import requests` and `import traceback as _traceback` at the module level (they were previously only available transitively via the service layer).

### `app/__init__.py`

Added `app.config['API_V14_TIMEOUT'] = config.get('API_V14_TIMEOUT', 5.0)` so the `API_V14_TIMEOUT` key set in `config.json` is actually loaded into Flask's config dict. Previously, `current_app.config.get('API_V14_TIMEOUT', 5.0)` always silently fell back to `5.0` because the key was never set.

## Error page behaviour summary

| Scenario | Before | After |
|---|---|---|
| API down, hitting `/processing-rules` | ~60 s wait → Werkzeug 500 debugger | ~5 s → friendly error page |
| API down, hitting `/listvars` | ~60 s wait → 500 | ~5 s → friendly error page |
| API up → cached, hitting any page | Instant (cache hit) | Unchanged |
| API up → cold cache | API call succeeds normally | Unchanged |

## Files Changed

| File | Change |
|---|---|
| `app/templates/_api_error.html` | New error template |
| `app/routes/main.py` | `import requests`, `import traceback as _traceback`, `_render_api_error()` helper, `handle_api14_error()` error handler |
| `app/__init__.py` | Load `API_V14_TIMEOUT` into `app.config` |

## Testing

1. With `api.omniture.com` unreachable, load `/processing-rules`. Verify the Codex error page renders within ~6 seconds with the friendly message visible and the traceback hidden under "Technical details".
2. Expand "Technical details" and verify the `ReadTimeout` stack trace is shown correctly.
3. Verify the "Try again" button links back to the same URL.
4. With the API reachable (or cache warm), confirm all affected pages load normally with no regressions.
