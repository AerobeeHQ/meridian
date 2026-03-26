# 028 — Components Panel on Dimension Detail Pages

**Date:** 2026-03-26
**Branch:** `feature/components-panel`
**Status:** Complete

---

## Summary

Added a "Components" panel to Prop, eVar, Event, and ListVar detail pages. The panel lists every Segment and Calculated Metric whose definition references the current dimension, with clickable links to each component's detail page.

This completes the cross-referencing picture: users can now see not only which Processing Rules set a variable (existing feature), but also which Segments filter on it and which Calculated Metrics are built from it.

---

## Problem

The todo item requested:
> Add a panel to the props/evars/events/listvar details pages (similar to the Related Processing Rules) named "Components", and lists Segments and Calculated Metrics that use that data dimension.

Without this panel, an analyst viewing `evar5` had no way of knowing (within Codex) that 3 segments and 2 calculated metrics depend on it.

---

## Approach

### Data source

Segment and Calculated Metric definitions are already fetched from Adobe Analytics API 2.0 and cached. The key insight was that both listing endpoints support `expansion=definition`, which includes the full JSON formula/container tree in each item returned by the listing call. Adding `definition` to the `expansion` parameter in `get_segments()` and `get_calculated_metrics()` means the cached listing data now contains enough information to do cross-referencing — no extra API calls needed on detail page load.

### Search strategy

For a given dimension (e.g. `variables/evar5` or `metrics/event3`), the Components helper function serialises each segment/metric definition to a JSON string and searches for the exact quoted variable ID:

```python
needle = f'"{variable_id}"'
if needle in json.dumps(definition):
    ...
```

Quoting the needle prevents false substring matches (e.g. `variables/prop1` matching `variables/prop10`).

### Async loading (same pattern as Processing Rules)

The panel uses the same async fragment pattern as "Related Processing Rules":
1. A spinner placeholder div is rendered in the initial HTML
2. A `fetch()` call hits `/api/components/<dimension_type>/<dimension_id>` after page load
3. The returned HTML fragment replaces the placeholder

This ensures a cold cache (no segments/calculated_metrics cached yet) does not block the detail page from loading — the panel simply shows "not available" with a link to visit the Segments or Metrics pages to warm the cache.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | Added `definition` to `expansion` in `get_segments()` and `get_calculated_metrics()`; added `definition` key to returned dicts |
| `app/routes/main.py` | Added `_find_components(rsid, variable_id)` helper; added `/api/components/<dimension_type>/<dimension_id>` route |
| `app/templates/_macros.html` | Added `components_section(components, segments_cached, calc_metrics_cached)` macro |
| `app/templates/_fragment_components.html` | New fragment template (mirrors `_fragment_related_rules.html`) |
| `app/templates/detail.html` | Added Components placeholder div + async fetch JS (Props and eVars) |
| `app/templates/event_detail.html` | Added Components placeholder div + async fetch JS |
| `app/templates/listvar_detail.html` | Added Components placeholder div + async fetch JS |
| `docs/todo.md` | Marked item as done |

---

## Variable ID Mapping

| Dimension Type | Example display ID | Searched variable ID |
|----------------|--------------------|----------------------|
| Prop | `prop3` | `variables/prop3` |
| eVar | `evar5` | `variables/evar5` |
| Event | `event2` | `metrics/event2` |
| ListVar | `1` (listvar_num) | `variables/listvar1` |

---

## Cache Behaviour

- `definition` is now stored in the `segments` and `calculated_metrics` cache entries
- **Existing cache files** (written before this change) will not have `definition` — the panel will show "not available" until the cache is refreshed
- Cache refresh: visit `/segments` or `/calculated-metrics` (which triggers `get_cached_data`), or use the force-refresh button, or wait for the 24h background warmer

---

## Notes

- Segments use `S` badge (info/blue); Calculated Metrics use `M` badge (success/green) to visually distinguish the two types at a glance
- The Components panel appears between "Related Processing Rules" and "Documentation Notes" in the left column of each detail page
- The feature is purely API 2.0 — no API 1.4 calls involved
