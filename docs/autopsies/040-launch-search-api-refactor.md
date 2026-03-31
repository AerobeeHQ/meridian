# Autopsy 040 — Launch Search API Refactor

**Date:** 2026-03-31
**Branch:** `main`
**Status:** Complete — pending commit

---

## Summary

Replaced the library-walk approach for the Adobe Launch integration (v2-003) with the Reactor `/search` API. Three bugs in the original implementation were identified and resolved. The new approach is faster, covers a broader set of resources, and is not scoped to the production library.

---

## Bugs Fixed

### Bug 1 — Only production library was searched

`get_analytics_actions()` called `get_production_library()` which filtered everything to the most recently updated published library. Rules that existed in the property but were not yet published (drafts, dev library, rules in progress) were invisible.

**Fix:** The `/search` API query uses `"attributes.revision_number": {"value": 0}`, which targets the current head state of all resources regardless of library membership.

### Bug 2 — Custom code actions were not detected

The library-walk approach only parsed structured `setVariables` actions (`adobe-analytics::actions::setVariables`). Variables set via `core::actions::custom-code` were silently missed — a common pattern in large Launch implementations.

**Fix:** The `/search` API searches `attributes.*` — full-text across all attribute fields including the `source` string in custom code components. Any resource whose attributes contain the dimension string (e.g. `eVar1`) is returned, regardless of delegate type.

### Bug 3 — Only eVars in extension config were reliably matched

`_parse_tracker_properties()` attempted to handle two known settings formats but real-world extension configurations sometimes diverged, causing props, events, and list variables to be missed.

**Fix:** With the search API, the settings JSON string is searched as text, not parsed and field-mapped. Format variations are irrelevant.

---

## Architecture Change

### Old approach (library walk)

```
GET /properties/{id}/libraries?filter[state]=EQ published
→  GET /libraries/{id}/extensions           (batch, 2 workers)
→  GET /libraries/{id}/rules                (batch, 2 workers)
→  GET /rules/{id}/rule_components          (N rules × 8 workers)
→  parse settings JSON → match variable name → cache as launch_rules
```

Cache key: one monolithic `launch_rules` key pre-warmed at startup and on a 24h schedule.

### New approach (search API)

```
POST /search   {"query": {"attributes.*": {"value": "eVar1"}, ...}}
→  GET /rules/{id}   (parallel, 8 workers, for rule_component matches only)
→  cache as launch_search_eVar1
```

Cache key: per-dimension (`launch_search_eVar1`, `launch_search_prop3`, etc.), fetched on demand when a detail page loads its fragment. TTL 1 hour.

### Why on-demand is better here

Pre-warming was appropriate when one query fetched everything. Now that each dimension is a separate search call, pre-warming would require iterating all dimensions in the report suite — many API calls for data that may never be viewed. On-demand caching with a 1-hour TTL is a better fit.

---

## New methods in `AdobeLaunchService`

| Method | Description |
|--------|-------------|
| `search_dimension(dimension_value, property_id, size=100)` | POST to `/search`, returns raw matched resource list |
| `get_rule(rule_id)` | GET a single rule by ID; returns the `data` object |
| `search_and_resolve(dimension_value, property_id)` | Orchestrates search + parallel rule-name resolution + deduplication |

### `search_and_resolve` result format

Each entry in the returned list:

```python
{
    "source":                 "rule" | "extension" | "data_element",
    "source_id":              str | None,   # extension/data-element ID for Launchpad deep link
    "rule_id":                str | None,   # rule ID for Launchpad deep link
    "rule_name":              str,
    "rule_enabled":           bool,
    "delegate_descriptor_id": str,          # e.g. "adobe-analytics::actions::setVariables"
}
```

`rule_component` entries are processed before `rules` entries so that, when both a component and a rule-name match exist for the same `rule_id`, the component (which carries the `delegate_descriptor_id`) takes precedence.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_launch.py` | Full rewrite — removed library-walk methods, added `search_dimension`, `get_rule`, `search_and_resolve` |
| `app/routes/main.py` | Removed `find_related_launch_rules()`; updated fragment endpoint to build dimension string and call `search_and_resolve` via per-dimension cache; updated `cache_view` to count `launch_search_*` keys |
| `app/services/cache_warmer.py` | Removed `launch_rules` from `CONFIG_CACHE_KEYS`; removed Launch warmer entry |
| `app/templates/cache.html` | Replaced "Cached Actions" row and "Refresh Launch Rules" button with "Search Cache" count and on-demand description |
| `app/templates/_macros.html` | Added `data_element` source type with badge and Launchpad deep link; updated "not available" message; added `delegate_descriptor_id` display below each result |

---

## Removed

| Removed item | Reason |
|---|---|
| `get_production_library()` | Library scoping replaced by search API |
| `get_library_extensions()` | Library scoping replaced by search API |
| `get_library_rules()` | Library scoping replaced by search API |
| `get_analytics_actions()` | Entire library-walk orchestration replaced by `search_and_resolve` |
| `_parse_settings()` | Settings JSON no longer parsed — text search handles format variants |
| `_extract_names()` | Same |
| `_parse_tracker_properties()` | Same |
| `find_related_launch_rules()` in `main.py` | Dimension matching now done by the search API, not post-filter |
| `launch_rules` cache key | Replaced by per-dimension `launch_search_{value}` keys |

---

## False Positive Risk

The `attributes.*` full-text search will match a dimension string wherever it appears in any attribute — including names, descriptions, and comments in custom code. A rule named "Clear eVar1 on exit" will appear in results even if it doesn't set eVar1, and a custom code condition that mentions eVar1 in a comment will also appear.

This is accepted. The `delegate_descriptor_id` is now shown below each result in the UI, which helps users distinguish structured setVariables assignments from free-text or condition matches.

---

## "Unknown Rule" — Two-Strategy Rule Resolver

The `/search` API does not always populate `relationships.rule.data.id` on `rule_component` results (observed on components with `core::conditions::custom-code` delegate). Without a rule ID, the batch fetch has nothing to query and the name falls back to "Unknown Rule".

**Fix (same session):** `search_and_resolve` now categorises each rule_component by resolution strategy before dispatching any fetches:

| Strategy | Condition | Fetch |
|----------|------------------------------------------------|-----------------------------------|
| A        | `relationships.rule.data.id` present           | `GET /rules/{id}`                 |
| B        | relationship ID absent, `links.rules` present  | `GET {links.rules}` → first item  |

Both strategies run in the same `ThreadPoolExecutor` pass. Results land in separate maps (`rule_map` keyed by rule ID, `comp_map` keyed by component ID). The entry-builder resolves strategy A first; if the rule ID was absent it looks up strategy B and also extracts the rule ID from the fetched data for the Launchpad deep link.

If both strategies fail (no relationship, no links.rules, or the fetch errors), the entry still appears but labelled "Unknown Rule" — the component is at least visible rather than silently dropped.
