# 039 — Reactor API Debug Page

**Date:** 2026-03-31
**Branch:** `feature/reactor-debug-page`
**Todo item:** "Add another Debug page for the Adobe Launch Reactor APIs"

---

## Problem

Codex already had an interactive debug page at `/debug` for Adobe Analytics API 1.4 and 2.0,
but there was no equivalent tool for the Adobe Launch Reactor API. Developers working with
Launch properties had to use external tools (Postman, curl) to explore and test Reactor API
endpoints, even though Codex already held the necessary credentials.

The todo listed eight feature requirements for this page:

1. Access-controlled to Reactor admin role
2. Same look and feel as the existing Analytics debug page
3. Make test API calls and display responses
4. Error handling for auth errors and invalid params
5. Clear parameter documentation with examples
6. Accessible from the nav under a new "Adobe Launch" section
7. Search functionality across endpoints
8. Help construct valid calls with examples and remembered values

---

## Approach

### Swagger source

The Reactor API is documented in `assets/swagger/adobe_reactor_api_swagger.yaml` (OpenAPI 3.1.0).
Unlike the Analytics swagger files which are JSON, this is YAML — so `pyyaml` was added as a
new dependency.

The YAML is parsed once at startup and cached (same pattern as `_load_debug_endpoints()`),
producing a flat list of 137 endpoint descriptors across 19 resource tags.

Each descriptor has the same shape as API 2.0 entries:

```python
{
    'api':         'reactor',
    'tag':         str,           # e.g. 'Properties', 'Rules'
    'http_method': str,           # e.g. 'GET', 'POST'
    'path':        str,           # e.g. '/properties/{PROPERTY_ID}/rules'
    'summary':     str,
    'params': [
        {
            'name':        str,
            'in':          str,   # 'path' or 'query' (headers skipped)
            'type':        str,
            'required':    bool,
            'description': str,
            'default':     any,
            'example':     any,
        },
        ...
    ],
}
```

**Header stripping:** Every Reactor endpoint lists `Authorization`, `x-api-key`,
`x-gw-ims-org-id`, and `Accept` as required headers — but these are injected by the
server-side proxy, so they are stripped from the user-facing parameter table.
This keeps the UI focused on the values users actually need to supply.

### New files and changes

| File | Change |
|---|---|
| `pyproject.toml` | Added `pyyaml>=6.0` |
| `app/services/adobe_launch.py` | Added `get_raw(path, params)` method for arbitrary GET calls |
| `app/routes/main.py` | Added `_load_reactor_endpoints()`, `/debug/reactor`, `/debug/reactor/call` |
| `app/templates/reactor_debug.html` | New template (same two-panel layout as `api_debug.html`) |
| `app/templates/base.html` | Added "Adobe Launch" section to the "More" nav dropdown |

### Access control (FR1)

Full user-level role checking is deferred to the v2-004 OAuth login milestone. For now,
both the `/debug/reactor` route and the nav link gate on `LAUNCH_ENABLED` — the page is
only reachable when the app is configured with Reactor credentials. Accessing it without
Reactor configured returns HTTP 403.

### Navigation (FR6)

The "More" dropdown was reorganised with section headers:

```
More
├── Report Suites
├── Cache
├── ─────────────────
├── Adobe Analytics
│   └── API Debug
├── ─────────────────   ← only when LAUNCH_ENABLED
└── Adobe Launch
    └── Reactor Debug
```

The `active_tab` check was extended to include `'reactor-debug'` so the "More" item
highlights correctly when on the Reactor page.

### Proxy route

`POST /debug/reactor/call` follows the same pattern as `POST /debug/call`:

1. Validate `LAUNCH_ENABLED` and the `codex_launch_service` instance
2. Reject non-GET methods
3. Substitute `{PARAM_NAME}` path placeholders from the request body
4. Delegate to `AdobeLaunchService.get_raw(path, params)` which attaches the correct
   IMS auth headers (`Authorization`, `x-api-key`, `x-gw-ims-org-id`, `Accept`)
5. Return `{success, data}` or `{success: false, error, error_type}`

### Template features

**FR5 — Parameter documentation:** The parameter table has an extra "Default / Example"
column populated from the swagger `schema.default` and `schema.example` fields. Path
parameters also show Reactor-style ID placeholders (`PRxx…`, `RLxx…`, etc.) based on
the parameter name, so it's immediately obvious what format each ID should take.

**FR7 — Search:** Full-text search across method, path, summary, and tag — same
implementation as the Analytics debug page.

**FR8 — Remembered values:** After every successful API call the request body is saved to
`localStorage` keyed by `reactor_debug:body:{METHOD}:{path}`. When an endpoint is
re-selected, the saved body is automatically restored. A `↺ Reset` button appears
whenever saved values are loaded, letting users revert to the generated template. A green
dot (●) in the endpoint list indicates endpoints that have saved values.

**FR2 — Consistent look:** The two-panel layout, method badges, tag-grouped accordions,
collapsible tags, Send/Copy buttons, and keyboard shortcut (⌘/Ctrl+Enter) all match
the existing `api_debug.html`.

---

## Testing checklist

- [ ] Navigate to More → Adobe Launch → Reactor Debug — page loads with 137 endpoints
- [ ] Search "properties" — filters to relevant endpoints
- [ ] Click `GET /companies` — params table shows `page[size]` / `page[number]` with defaults
- [ ] Click `GET /properties/{PROPERTY_ID}/rules` — PROPERTY_ID is pre-filled with the configured property
- [ ] Send `GET /companies` — response body displayed with green badge
- [ ] Send `POST /search` — rejected with "POST requests are disabled" error
- [ ] Verify saved-values dot appears on endpoint after a successful call
- [ ] Click Reset — body reverts to template, dot disappears
- [ ] Set `LAUNCH_ENABLED=false` — Reactor Debug link hidden from nav, `/debug/reactor` returns 403
- [ ] Verify `uv run verify_setup.py` passes

---

## Bugs found / edge cases

**Reactor swagger tag `(NEW) Interactive API documentation`** — the swagger includes a
descriptive tag that isn't a real resource group. It appears in the sorted tag list.
Low impact; the tag contains no endpoints.

**`page[size]` and `page[number]` in request body:** The square-bracket syntax passes
through the proxy as URL query params via `requests` — no escaping needed since `requests`
handles encoding automatically.
