# Plan: Processing Rules Integration on Detail Pages

**Roadmap item:** When viewing a Prop, eVar, Event, or ListVar, show which Processing Rules set or alter that dimension.

**Complexity: Medium**

---

## Overview

Processing rules data is already fetched and cached (`/processing-rules` route, `get_processing_rules()` in `adobe_analytics.py`). The rules have conditions and actions stored as formatted text strings. The work is to cross-reference those strings against the current dimension when rendering a detail page, then surface the matches in the UI.

---

## Current State

- `GET /processing-rules` fetches and caches all rules for the configured RSID.
- Each rule is a dict with `title`, `rules` (conditions), `actions`, `matchOn`, `comment`.
- Conditions and actions are formatted as multi-line strings (e.g. `"Set eVar3 to value of querystring param 'cid'"`).
- Detail pages (`/props/<id>`, `/evars/<id>`, `/events/<id>`, `/listvars/<name>`) currently have no reference to processing rules.

---

## Implementation Plan

### Step 1 — Helper: find matching rules for a dimension

Add a utility function (in `main.py` or a new `app/services/processing_rules.py`) that:

1. Accepts the cached processing rules list and a dimension identifier (e.g. `prop3`, `eVar5`, `event2`, `list1`).
2. Searches the `rules` (conditions) and `actions` strings of each rule for the dimension name, using case-insensitive matching against common patterns:
   - Exact variable name: `eVar5`, `prop3`, `event2`, `list1`
   - Adobe variable syntax: `v5`, `c3`, `events` (for events), `l1`
3. Returns a list of matching rule dicts (`title`, `conditions`, `actions`, `comment`).

**Edge cases:**
- `eVar10` should not match `eVar1` — use word-boundary or full token matching.
- Events may appear as `event2` or inside a comma-separated events list (`event1,event2,event3`).

### Step 2 — Load processing rules in detail page routes

In each detail page route (`/props/<id>`, `/evars/<id>`, `/events/<id>`, `/listvars/<name>`):

1. Load the cached processing rules using `cache.get_or_set(rsid, 'processing_rules', fetch_fn)` — same call used on the `/processing-rules` list page.
2. Call the helper from Step 1 to get `related_rules`.
3. Pass `related_rules` to the template context.

The fetch is cache-backed, so this adds no extra API calls in the common case.

### Step 3 — Template: add "Related Processing Rules" section

In `detail.html`, `event_detail.html`, and `listvar_detail.html`, add a collapsible section below the configuration table:

```
## Related Processing Rules

| # | Rule Title | Conditions | Actions | Notes |
|---|-----------|------------|---------|-------|
| 1 | Set campaign eVar | ... | ... | ... |
```

- If `related_rules` is empty, show a muted "No processing rules reference this dimension."
- Use the same monospace styling as the `/processing-rules` list page.
- Section is collapsed by default (Bootstrap accordion or `<details>`) to avoid visual clutter.

---

## Files to Change

| File | Change |
|------|--------|
| `app/routes/main.py` | Add `find_related_processing_rules()` helper; call it in each detail route |
| `app/templates/detail.html` | Add Related Processing Rules section |
| `app/templates/event_detail.html` | Add Related Processing Rules section |
| `app/templates/listvar_detail.html` | Add Related Processing Rules section |

---

## Risks & Notes

- **Matching accuracy:** Processing rule text is human-written and inconsistent. String matching will catch most cases but may miss unusual variable references. A best-effort approach is acceptable for v2.
- **No API changes needed** — all data is already available in the processing rules cache.
- **Performance:** Cache-backed, negligible overhead.
