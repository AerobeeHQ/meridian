# 048 — Trendline Data Accuracy (dimension-scoped trend charts)

**Date:** 2026-04-03
**Branch:** `fix/trendline-data-accuracy`
**Status:** Complete

---

## Problem

The 30-day trendline chart shown on every prop, eVar, event, and listVar detail page displayed peaks and valleys even for variables that had **no recent data**.

The reported bug read:
> "When a prop/evar/event/listvar doesn't have any recent data, the trendline chart still shows peaks and valleys. What is this data? If there is none, it should be showing a flatline."

---

## Root Cause

`AdobeAnalyticsV2Service.get_dimension_trend()` accepted a `dimension` parameter (e.g. `variables/prop15`) but **never used it in the API request body**. The actual report request was:

```json
{
  "dimension": "variables/daterangeday",
  "metricContainer": {
    "metrics": [{"id": "metrics/occurrences"}]
  },
  "globalFilters": [{"type": "dateRange", "dateRange": "..."}]
}
```

This asks Adobe Analytics: *"how many total occurrences per day across the entire report suite?"* — completely independent of which variable was being viewed. The result is overall site traffic, which always has peaks and valleys.

Because every detail page showed the same underlying data (whole-suite traffic), the chart was both misleading and meaningless for the actual variable. A variable with zero real data in the last 30 days still showed a busy-looking chart.

---

## Solution

Added a static helper method `_dimension_exists_filter(dimension)` that builds an inline segment `globalFilter` restricting the report to **hits where the specific dimension has a value** (is not Unspecified/not-set).

### Segment predicate format

The Adobe Analytics API 2.0 supports inline `segmentDefinition` objects inside `globalFilters`. The predicate grammar for "dimension exists" differs by variable type:

| Variable type | `pred.func` | `val.func` |
|--------------|-------------|------------|
| prop, eVar, listVar | `exists` | `attr` |
| event | `event-exists` | `event` |

The helper detects events by checking whether `dimension.startswith('variables/event')`.

### New request body

```json
{
  "dimension": "variables/daterangeday",
  "metricContainer": {
    "metrics": [{"id": "metrics/occurrences"}]
  },
  "globalFilters": [
    {"type": "dateRange", "dateRange": "..."},
    {
      "type": "segment",
      "segmentDefinition": {
        "container": {
          "func": "container",
          "context": "hits",
          "pred": {
            "func": "exists",
            "val": {"func": "attr", "name": "variables/prop15"}
          }
        }
      }
    }
  ]
}
```

For a variable with no recent data, the API now correctly returns all-zero rows (or an empty rows array), producing a flatline chart instead of reporting suite-wide traffic.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | Added `_dimension_exists_filter()` static method; updated `get_dimension_trend()` to pass the dimension filter in `globalFilters` |
| `docs/todo.md` | Marked trendline bug as fixed |

---

## Notes

- **Cache invalidation:** Existing cached trend data (keyed `core_trend_*`, `prop_trend_*`, `evar_trend_*`, `listvar_trend_*`) will be served until the TTL expires. After expiry, the next request re-fetches with the corrected query.
- **Events vs dimensions:** Events use `event-exists` / `val.func: "event"` rather than `exists` / `val.func: "attr"`. This distinction mirrors the predicate grammar used in the existing `_walk_segment_definition` parser in `main.py`.
- **No template changes needed:** The `trend_chart_js` macro already renders a flat chart when all values are zero; it just wasn't receiving zeros before.
