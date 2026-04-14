# 053 — Multisite Internal Link Audit

**Date:** 2026-04-15
**Branch:** `fix/multisite-internal-links`
**Status:** Complete

---

## Problem

PR #67 added per-client URL prefixes (`/<client>/`) to all routes, and PR nav-links were updated in `base.html`. However, every other internal link in the app remained as a bare path (e.g. `/evars/evar1`, `/segments`, `/cache/clear`). These all produced 404s because the routes no longer live at the root.

Affected surfaces:
- Listing page → detail page links (all dimension types, segments, calculated metrics)
- Detail page → cache refresh buttons
- Detail page → dimension cross-links (eVar/prop/event references in segment and metric definitions)
- Detail page → classification sub-links
- Overview page → all stat-card and section links, recent-notes links, cache status links
- `_macros.html` component panel → segment and metric cross-links, "load" buttons for processing rules and channel rules
- `back_url` values passed from Python to templates (detail page back-links)
- Cache-refresh fallback redirect in Python
- JavaScript `fetch()` calls in detail templates — async panel loads (processing rules, Launch rules, channel rules, components, notes, tags) all used bare `/api/...` paths

---

## Architectural Decision

Two consistent rules — one per context:

### Templates → `{{ client_slug }}` prefix

```html
<a href="/{{ client_slug }}/evars/{{ row[col] }}">{{ row[col] }}</a>
```

`client_slug` is injected into every template via the `inject_globals` context processor. Explicit string interpolation was chosen over `url_for()` in templates because:
- It matches the pattern already established in `base.html`
- It's readable — the intent is obvious without knowing endpoint function names
- Detail-page links carry dynamic parameters that make `url_for()` more verbose without adding value
- The Jinja2 `~` operator handles string concatenation cleanly in the `set` context (`overview.html` stat cards)

The same rule applies to JavaScript `fetch()` calls inside `<script>` blocks. Jinja2 renders before the browser parses the JS, so `{{ client_slug }}` resolves to a plain string in the generated output:

```js
fetch('/{{ client_slug }}/api/related-rules/{{ dimension_type }}/{{ dimension_id }}')
```

This works even when the surrounding JS uses template literals (`\`...\``) with its own `${var}` interpolation — the two syntaxes don't conflict.

### Python → `url_for('main.endpoint')`

```python
back_url=url_for('main.evars'),
return redirect(request.referrer or url_for('main.overview'))
```

In Python, `url_for()` is the right tool because:
- Flask's `url_defaults` hook automatically injects the current `client` slug — no manual prefixing needed
- It's immune to route path changes: if a route is renamed, only the decorator needs updating, not the call sites
- String manipulation of paths in Python is fragile and bypasses the routing system entirely

---

## Scope

64 locations across 12 files fixed across two passes.

### Pass 1 — hrefs and Python (46 locations)

| File | Links fixed |
|------|------------|
| `app/templates/listing.html` | 7 detail-page hrefs + JS cache-refresh button |
| `app/templates/overview.html` | Stat-card links, 4 section links, recent-notes, cache manage/clear |
| `app/templates/cache.html` | Clear-all + per-key refresh links |
| `app/templates/detail.html` | Cache-refresh button, classification cross-links |
| `app/templates/event_detail.html` | Cache-refresh button |
| `app/templates/listvar_detail.html` | Cache-refresh button |
| `app/templates/segment_detail.html` | Cache-refresh, eVar/prop/event cross-links |
| `app/templates/calc_metric_detail.html` | Cache-refresh, event/segment formula reference links |
| `app/templates/_macros.html` | Segments/metrics warm-cache nudge, processing-rules and channel-rules "load" buttons, component accordion links |
| `app/templates/_api_error.html` | Cache page link |
| `app/routes/main.py` | 7× `back_url` + 1× redirect fallback → `url_for()`; added `url_for` to Flask import |

### Pass 2 — JavaScript fetch() calls (18 locations)

Discovered after the first pass when detail pages loaded successfully but their async panels (processing rules, Launch rules, channel rules, components, notes, tags) returned 404 — the JS `fetch()` calls were also using bare `/api/...` paths.

| File | Fetch calls fixed |
|------|-----------------|
| `app/templates/detail.html` | 4 (related-rules, related-launch-rules, related-channel-rules, components) |
| `app/templates/event_detail.html` | 4 (same panels) |
| `app/templates/listvar_detail.html` | 4 (same panels) |
| `app/templates/_macros.html` | 6 (tags CRUD, notes options, notes load/save) |

---

## Verification

- `uv run verify_setup.py` passes (all checks green) after both passes
- Final grep for bare `href="/[a-z]"` patterns in templates: zero results
- Final grep for bare `fetch('/api` and `fetch(\`/api` patterns in templates: zero results

---

## Notes

- The `href="/"` in `_api_error.html` (← Home button) was left as `/` — root redirects to the first client anyway, and `client_slug` may be empty on fatal startup errors.
- The `back_url` pattern (Python passes a pre-built URL to the template) continues to work correctly because `url_for()` inside a Flask request context always has access to `url_defaults`.
- If a new detail-page template is added, the rule is: use `href="/{{ client_slug }}/your-path"` for all internal links and `fetch('/{{ client_slug }}/api/...')` for all AJAX calls. The `client_slug` variable is always available via `inject_globals`.
- `url_for` was missing from the Flask import line in `main.py` — adding it to `back_url` calls introduced a `NameError` at runtime. It has been added to the import.
