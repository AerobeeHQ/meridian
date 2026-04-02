# 046 — API Debug: Allow Read-Only POST Endpoints

**Date:** 2026-04-03
**Branch:** `fix/api-debug-allow-readonly-post`
**Status:** Complete

---

## Problem

The API Debug page (`/debug`) blocked all non-GET requests for the Analytics API 2.0. This broke the most important endpoint in the entire 2.0 API: `POST /reports`, which is used to run analytics queries. The Adobe Analytics 2.0 Reporting API requires POST by design — there is no GET equivalent.

The open bug read:
> "We block the API debug page from sending POST requests, but some (or all, who really knows) can't actually change any data. That's just how you make a read-only call to those endpoints."

The Reactor debug page (`/debug/reactor`) already had a partial solution: `POST /search` was explicitly whitelisted there (autopsy 040). The same pattern needed to be applied to the Analytics debug page.

---

## Investigation

Audited all POST endpoints in `adobe_analytics_api_2.0_swagger.json`:

| Path | Summary | Verdict |
|------|---------|---------|
| `/annotations` | Create new annotation | ❌ Write |
| `/calculatedmetrics` | Create calculated metric | ❌ Write |
| `/calculatedmetrics/validate` | Validate metric definition | ✅ Read-only |
| `/componentmetadata/shares` | Share component with user | ❌ Write |
| `/componentmetadata/shares/component/search` | Search shares | ✅ Read-only |
| `/componentmetadata/tags` | Create tags | ❌ Write |
| `/componentmetadata/tags/component/search` | Search tags | ✅ Read-only |
| `/dateranges` | Create a date range | ❌ Write |
| `/projects` | Create a project | ❌ Write |
| `/projects/validate` | Validate project definition | ✅ Read-only |
| `/reports` | Run a report | ✅ Read-only |
| `/reports/realtime` | Run a realtime report | ✅ Read-only |
| `/segments` | Create a segment | ❌ Write |
| `/segments/validate` | Validate segment definition | ✅ Read-only |

---

## Solution

### Backend — `app/routes/main.py`

Replaced the blanket `http_method not in ('GET',)` block with a two-tier check, mirroring the Reactor debug pattern:

```python
_ALLOWED_POST_PATHS = {
    '/reports',
    '/reports/realtime',
    '/calculatedmetrics/validate',
    '/segments/validate',
    '/projects/validate',
    '/componentmetadata/shares/component/search',
    '/componentmetadata/tags/component/search',
}
if http_method == 'POST' and path_template not in _ALLOWED_POST_PATHS:
    return jsonify({'success': False, 'error': 'POST is only enabled for read-only endpoints ...'})
if http_method not in ('GET', 'POST'):
    return jsonify({'success': False, 'error': f'{http_method} requests are disabled ...'})
```

PUT, DELETE, and PATCH remain fully blocked. Unknown POST paths (create operations) are also blocked.

### Frontend — `app/templates/api_debug.html`

**`isReadOnly(ep)`** — updated to enable the Send button for whitelisted POST paths:

```js
const ALLOWED_POST_PATHS = new Set(['/reports', '/reports/realtime', ...]);

function isReadOnly(ep) {
    if (ep.api === '1.4') return true;
    if (ep.http_method === 'GET') return true;
    if (ep.http_method === 'POST' && ALLOWED_POST_PATHS.has(ep.path)) return true;
    return false;
}
```

**`buildTemplate(ep)`** — added starter request bodies for the two most common POST endpoints:

- `POST /reports` — pre-fills a minimal ranked report (last 7 days, pageviews by page dimension, limit 10).
- `POST /reports/realtime` — pre-fills a minimal realtime query (pageviews by page).

These give users a working starting point without needing to know the report request schema.

**Button tooltip** — updated the disabled-button tooltip to accurately describe which POSTs are permitted.

---

## Changes

| File | Change |
|------|--------|
| `app/routes/main.py` | Replace blanket POST block with `_ALLOWED_POST_PATHS` allowlist; also allow PUT/DELETE/PATCH block to remain |
| `app/templates/api_debug.html` | Add `ALLOWED_POST_PATHS` constant; update `isReadOnly()`; add starter templates for `/reports` and `/reports/realtime`; update disabled-button tooltip |
| `docs/todo.md` | Mark API debug POST bug as fixed |

---

## Notes

- The `ALLOWED_POST_PATHS` set in the JS and the `_ALLOWED_POST_PATHS` set in Python must stay in sync. A comment in each references the other.
- API 1.4 endpoints are unaffected — they all use POST by the SOAP convention and were never blocked.
- The `/reports` starter body uses `LAST_7_DAYS` as the date range. Users will need to replace the dimension and metrics with values appropriate for their report suite.
