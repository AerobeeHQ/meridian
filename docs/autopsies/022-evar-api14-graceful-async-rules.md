# 022 — Graceful API 1.4 Failure + Async Processing Rules

**Date:** March 25, 2026
**Status:** Completed
**Branch:** `fix/evar-api14-graceful-async-rules`
**Depends on:** `fix/processing-rules-cache-state` (autopsy 021)

## Problems

### 1. Hard crash when API 1.4 is unavailable

Visiting `/evars/evar1` while `api.omniture.com` was unreachable threw:

```
requests.exceptions.HTTPError: 500 Server Error: Internal Server Error
for url: https://api.omniture.com/admin/1.4/rest/?method=ReportSuite.GetEvars
```

The exception propagated through `future.result()` in `evar_detail`, which had no error handling. The entire page render failed. The `listvar_detail` route already had a `try/except` around its futures loop — `evar_detail` did not.

### 2. Processing rules section tightly coupled to page render

The processing rules section was computed synchronously at page-render time. While the cache lookup itself is fast, this architectural choice meant the two concerns were coupled: if anything before the rules lookup failed, the whole page failed. It also made future changes (e.g. slower lookups, on-demand refresh) harder.

## Fixes

### Fix 1 — Try/except in `evar_detail` (app/routes/main.py)

The `ThreadPoolExecutor` futures loop now wraps each `future.result()` call:

```python
try:
    value = future.result()
except Exception as exc:
    logger.warning("evar_detail: failed to fetch '%s' for %s — %s", key, display_id, exc)
    value = None
```

Failed fetches set their variable to `None`. Crucially, `None` values are **not written to the cache** — on the next request the app retries the API rather than caching a failure. The existing `if evar_config:` guard in the merge block below already handled `None` gracefully, so no template changes are needed for the eVar config fields.

### Fix 2 — Processing rules section moved to async fetch

**New endpoint: `GET /api/related-rules/<dimension_type>/<dimension_id>`**

Reads from the local `processing_rules` cache key, runs `find_related_processing_rules()`, and returns the HTML fragment rendered by the new `_fragment_related_rules.html` template. This is a pure in-memory operation — no API calls. Response time is in the single-digit milliseconds.

| `dimension_type` | `dimension_id` | Search terms used |
|---|---|---|
| `prop` | e.g. `prop3` | `prop3` |
| `evar` | e.g. `evar5` | `evar5` |
| `event` | e.g. `event2` | `event2` |
| `listvar` | listvar number, e.g. `1` | `list1`, `listvar1` |

**New template: `_fragment_related_rules.html`**

A two-line template that delegates to the existing `related_processing_rules_section` macro. Reuses all three display states from autopsy 021 (warning banner, no-match message, accordion).

**Detail templates updated** (`detail.html`, `event_detail.html`, `listvar_detail.html`)

The synchronous macro call is replaced with a loading placeholder:

```html
<div id="related-rules-placeholder" class="card mb-4">
    <div class="card-body">
        <h5 class="card-title">Related Processing Rules</h5>
        <p class="text-muted mb-0 small">
            <span class="spinner-border spinner-border-sm me-1" ...></span>
            Loading…
        </p>
    </div>
</div>
```

A small IIFE in `{% block scripts %}` fetches the fragment and splices it in using `insertAdjacentHTML` + `remove()`:

```javascript
fetch('/api/related-rules/{{ dimension_type }}/{{ dimension_id }}')
    .then(function (r) { return r.text(); })
    .then(function (html) {
        placeholder.insertAdjacentHTML('afterend', html);
        placeholder.remove();
    })
    .catch(function () {
        placeholder.querySelector('.card-body').innerHTML =
            '<h5 ...>Related Processing Rules</h5>' +
            '<p ...>Could not load processing rules data.</p>';
    });
```

**Routes simplified**: `related_rules` and `processing_rules_cached` computation removed from all four detail routes. The endpoint is now the single source of truth for this section.

## Sequence After These Changes

```
Browser requests /evars/evar1
  → Flask renders detail.html (API 2.0 only for core fields)
  → If evar_config fetch fails → logs warning, renders page without
    merchandising/allocation data; no crash
  → Browser renders page with spinner in Related Processing Rules card
  → Browser fires fetch('/api/related-rules/evar/evar1')
  → Endpoint reads local cache (< 1ms), returns HTML fragment
  → Browser replaces spinner with rendered section
```

## Files Changed

| File | Change |
|---|---|
| `app/routes/main.py` | `evar_detail` try/except; new `/api/related-rules/` route; removed processing-rules blocks from all 4 detail routes |
| `app/templates/_fragment_related_rules.html` | New 2-line fragment template |
| `app/templates/detail.html` | Spinner placeholder + async fetch JS |
| `app/templates/event_detail.html` | Spinner placeholder + async fetch JS |
| `app/templates/listvar_detail.html` | Spinner placeholder + async fetch JS |

## Testing

1. **Crash fix:** With `api.omniture.com` unreachable, load `/evars/evar1`. Verify the page renders (with N/A for allocation/expiration/merchandising) rather than returning a 500 error.
2. **Async load:** Load any detail page and confirm the spinner appears briefly, then the Related Processing Rules card populates.
3. **Cold cache:** Visit a detail page before visiting `/processing-rules`. Confirm the warning banner renders after the spinner resolves.
4. **Warm cache with matches:** Visit `/processing-rules` first, then a dimension that is referenced. Confirm the accordion renders correctly.
