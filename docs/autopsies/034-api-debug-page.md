# 034 — Interactive API Debug Page

**Date:** 2026-03-27
**Branch:** `feature/api-debug-page`
**Status:** Complete

---

## Problem

There was no way to interactively explore the Adobe Analytics API from within Codex. Debugging an API call or checking what a specific endpoint returns required switching to a separate tool (Postman, curl, notebooks), re-entering credentials, and manually constructing requests. This friction slowed down development and made it harder for analysts to understand the raw data behind the app.

The todo item asked for a debug page covering all endpoints described in the two Swagger specs bundled with the project:

- `docs/adobe_analytics_api_1.4_swagger.json`
- `docs/adobe_analytics_api_2.0_swagger.json`

---

## Approach

Build a browser-based API explorer at `/debug` that:

1. Parses both Swagger specs server-side at startup.
2. Serialises the full endpoint list as JSON into the page template.
3. Renders a two-panel layout: endpoint browser (left) + request/response editor (right).
4. Proxies all API calls through the Flask server, so credentials never leave the backend.
5. Restricts execution to read-only methods (GET for 2.0, all 1.4 methods).

---

## Implementation

### `app/routes/main.py`

**`_DOCS_DIR`** — module-level constant resolving the absolute path to the `docs/` directory regardless of working directory:

```python
_DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'docs',
)
```

**`_load_debug_endpoints()`** — parses both specs and returns a flat list of endpoint descriptor dicts. Results are stored as a function attribute (`_load_debug_endpoints._cache`) so the 196-endpoint list is only parsed once per server process.

*API 1.4 parsing:* The 1.4 spec uses a custom path format (`/method=MethodName`) rather than standard REST paths. Each endpoint's request body is described via a `$ref` into `components/schemas`. A recursive `_resolve()` helper (max depth 4) walks the schema tree, resolving `$ref` pointers and collecting property names and types into a flat `{name: type}` dict used to pre-fill the request body textarea.

*API 2.0 parsing:* Standard OpenAPI `parameters` arrays. Each parameter is normalised to `{name, in, type, required, description}`. The `{globalCompanyId}` path segment and its corresponding parameter are stripped — the server inserts the company ID automatically.

Each descriptor has the shape:

```python
# API 1.4
{'api': '1.4', 'tag': str, 'method': str, 'summary': str, 'params': dict}

# API 2.0
{'api': '2.0', 'tag': str, 'http_method': str, 'path': str, 'summary': str, 'params': list}
```

**`/debug` route** — calls `_load_debug_endpoints()`, serialises the list to JSON, and renders `api_debug.html` with `endpoints_json`, `rsid`, and `configured_api_version`.

**`/debug/call` route (POST)** — API proxy endpoint:

- For **API 1.4**: delegates to `svc._make_request(method, body)` directly.
- For **API 2.0**: extracts `{paramName}` placeholders from the path template and substitutes them from the request body using `re.findall` + `dict.pop()`, so path parameters aren't URL-encoded into the query string. Remaining body keys are passed as query params.
- **Write method guard (server-side):** `http_method not in ('GET',)` returns a `success: False` response before any API call is made. This is defence-in-depth — the UI also prevents triggering write methods, but the backend enforces it independently.

### `app/templates/api_debug.html` (new)

Two-column Bootstrap layout within a single `min-height: 75vh` row:

**Left panel — endpoint browser:**
- API version radio toggle (1.4 / 2.0), defaulting to the configured API version.
- Live-filter search box.
- Endpoint list grouped by tag with collapse/expand accordions. Tags with a currently-selected endpoint or an active search are expanded automatically.

**Right panel — request/response editor:**
- Shows placeholder text until an endpoint is selected.
- On selection: endpoint title (with HTTP method badge for 2.0), summary, parameters reference table, and a pre-filled JSON body textarea.
- `buildTemplate(ep)` auto-populates the textarea: rsid fields are filled with the configured default RSID; array/boolean/integer fields get typed defaults.
- **Write method guard (frontend):** `isReadOnly(ep)` returns `true` for all API 1.4 endpoints and for 2.0 GET endpoints. The Send button is disabled and styled as secondary for non-read-only endpoints.
- `sendRequest()` and the `Cmd/Ctrl+Enter` keyboard shortcut both check `isReadOnly()` before sending.
- Response viewer shows elapsed time, a success/error badge, the formatted JSON response, and a copy-to-clipboard button.

### `app/templates/base.html`

Added an **API Debug** link to the More dropdown with correct `active_tab` highlighting:

```html
<li><a class="dropdown-item {% if active_tab == 'debug' %}active{% endif %}" href="/debug">API Debug</a></li>
```

The More dropdown toggle was also updated to include `'debug'` in its active-state condition.

### `Dockerfile`

Added `COPY docs/ docs/` so the Swagger spec files are bundled into the Docker image. Without this, `os.path.exists()` returned `False` for both spec paths in the container and the endpoint list was empty.

---

## Bugs Found and Fixed During Development

### Path parameter URL-encoding (`GET /dimensions/{id}`)

**Problem:** Selecting `GET /dimensions/{id}` and populating the `id` field would send the request to `/dimensions/%7Bid%7D` (with braces URL-encoded) instead of substituting the actual value.

**Root cause:** The path template string `"/dimensions/{id}"` was passed directly to `_make_request`, which URL-encodes any `{` or `}` characters in the path.

**Fix:** Before calling `_make_request`, extract `{paramName}` tokens with `re.findall(r'\{(\w+)\}', path_template)`, substitute each from the body dict (via `.pop()`), and pass the remaining body keys as query params.

### Empty endpoint list in Docker

**Problem:** The debug page loaded but showed no endpoints when running in Docker.

**Root cause:** The `Dockerfile` only copied `app/`, `exports/`, `config.json`, and `run.py` — the `docs/` directory containing the Swagger JSON files was never added to the image.

**Fix:** Added `COPY docs/ docs/` to the Dockerfile.

---

## Design Decisions

**Read-only restriction:** POST, PUT, DELETE, and PATCH endpoints are visible in the browser for reference (parameter inspection, request body templating) but cannot be executed. This prevents accidental data mutation through the service account credential, which may have write access. The restriction is enforced at both the UI layer (disabled button) and the server layer (HTTP 200 with `success: false` error response before any API call).

**Server-side proxy:** All requests go through `/debug/call` rather than calling Adobe's API directly from the browser. This avoids CORS issues and ensures credentials remain server-side.

**Startup parsing:** Both Swagger specs are parsed once at first page request and cached for the process lifetime. The 1.4 spec is ~400 KB and the 2.0 spec is ~188 KB; parsing takes a negligible amount of time but caching avoids repeated file I/O on every page load.

---

## Files Changed

| File | Change |
|------|--------|
| `app/routes/main.py` | `_DOCS_DIR`, `_load_debug_endpoints()`, `/debug` route, `/debug/call` proxy route |
| `app/templates/api_debug.html` | New — two-panel debug UI |
| `app/templates/base.html` | API Debug link in More dropdown |
| `Dockerfile` | `COPY docs/ docs/` to include Swagger specs in the image |

---

## Testing

1. Navigate to `/debug`. Verify the endpoint list loads with both API 1.4 and 2.0 groups.
2. Toggle the API version radio — verify the list switches and the panel resets.
3. Type in the search box — verify live filtering across method name, path, and summary.
4. Select an API 1.4 endpoint — verify Send button is enabled (primary style) and the body template is pre-filled.
5. Select a 2.0 GET endpoint — verify Send button is enabled. Click Send and verify a JSON response appears with elapsed time.
6. Select `GET /dimensions/{id}` — enter a valid dimension ID (e.g. `variables/evar1`) in the body. Verify the request resolves correctly and does not return a 404.
7. Select a 2.0 POST endpoint — verify the Send button is disabled (secondary style) with a tooltip explaining why.
8. Attempt to POST to `/debug/call` with `http_method: "POST"` — verify the server returns `success: false` without calling the Adobe API.
9. Verify `Cmd/Ctrl+Enter` in the textarea sends the request for a GET endpoint and does nothing for a POST endpoint.
10. Rebuild the Docker image and verify endpoints load correctly in the containerised deployment.
