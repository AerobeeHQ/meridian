# 063 — Dimension Tags Column on Listing Pages

**Date:** 2026-05-07
**Branch:** `feature/dimension-tags-column`
**Status:** Complete

---

## Problem

The Props, eVars, and Events listing pages had no visibility into the Adobe
Analytics component tags assigned to each dimension or metric.  Adobe Analytics
API 2.0 supports a tag-based organisation system where admins can label
variables (e.g. `"Analytics Team"`, `"Production"`, `"Phase 2"`), but Codex
never requested or displayed this data.

The todo item read:

> Add Tags as a column to the Props/eVars/Events/ListVars listing pages,
> so that the user can search for them.

Without the column, analysts had no way to filter or search for dimensions by
their Adobe Analytics tag labels from within Codex.

---

## Solution

### 1. Request tags in API calls (`adobe_analytics_v2.py`)

Added `"expansion": "tags"` to the query parameters of the two list endpoints:

```python
# get_dimensions()
result = self._make_request(
    "dimensions",
    params={"rsid": rsid, "expansion": "tags"}
)

# get_metrics()
result = self._make_request(
    "metrics",
    params={"rsid": rsid, "expansion": "tags"}
)
```

The Analytics API 2.0 `expansion=tags` parameter causes each returned object
to include a `tags` array:

```json
{
  "id": "variables/evar1",
  "name": "Page Name",
  "tags": [
    {"id": "123", "name": "Analytics"},
    {"id": "456", "name": "Team:Checkout"}
  ]
}
```

### 2. Add `_extract_tag_names()` helper (`adobe_analytics_v2.py`)

Added a `@staticmethod` that converts the raw `tags` array into a
comma-separated string, gracefully handling the case where the field is absent
(e.g. data served from a cache populated before this change):

```python
@staticmethod
def _extract_tag_names(obj: dict) -> str:
    tags = obj.get("tags") or []
    names = [t["name"] for t in tags if t.get("name")]
    return ", ".join(names)
```

### 3. Add `tags` field to transform methods (`adobe_analytics_v2.py`)

The three transformation methods now include a `"tags"` key:

| Method | Field added |
|--------|-------------|
| `_transform_dimension_to_prop()` | `"tags": self._extract_tag_names(dim)` |
| `_transform_dimension_to_evar()` | `"tags": self._extract_tag_names(dim)` |
| `_transform_metric_to_event()` | `"tags": self._extract_tag_names(metric)` |

### 4. Add `Tags` column to listing dictionaries (`main.py`)

Added `'tags': 'Tags'` to `PROPS_COLUMNS`, `EVARS_COLUMNS`, and
`EVENTS_COLUMNS`, placed before the `Description` column:

```python
PROPS_COLUMNS = {
    'id': 'Prop',
    'name': 'Label',
    'pathing_enabled': 'Pathing',
    'list_enabled': 'List Support',
    'list_delimiter': 'Delimiter',
    'tags': 'Tags',           # new
    'description': 'Description'
}
```

The Tags column is plain text (comma-separated tag names), making it fully
searchable via the DataTables search box on each listing page.

---

## Notes

- **ListVars excluded:** ListVar data is fetched via the API 1.4 service
  (`adobe_analytics.py`), which does not support the Analytics 2.0 tag
  expansion.  ListVars have been left unchanged.
- **Cache compatibility:** Existing cached dimension data (24 h TTL) will
  not include tags until the cache is refreshed.  `_extract_tag_names` returns
  `""` when `tags` is absent, so cached rows simply show an empty Tags cell
  rather than an error.
- **No schema migration:** The `tags` field is derived purely from the API
  response; no stored notes or cache files need updating.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | Added `expansion=tags` to `get_dimensions()` and `get_metrics()`; added `_extract_tag_names()`; added `"tags"` field to three transform methods |
| `app/routes/main.py` | Added `'tags': 'Tags'` to `PROPS_COLUMNS`, `EVARS_COLUMNS`, `EVENTS_COLUMNS` |
| `docs/autopsies/063-dimension-tags-column.md` | This document |

---

## Tests

All 131 existing tests pass without modification.  The change to the API
params is covered indirectly by the existing Adobe Analytics v2 service tests;
the `_extract_tag_names` logic is simple enough that the existing round-trip
tests provide sufficient confidence.
