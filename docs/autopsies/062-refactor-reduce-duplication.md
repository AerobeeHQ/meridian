# 062 — Refactor: Reduce Code Duplication

**Date:** 2026-05-06
**Branch:** `refactor/reduce-duplication`
**Status:** Complete

---

## Problem

Three areas of the codebase contained clear copy-paste duplication that made
the code harder to maintain:

### 1. `adobe_analytics_v2.py` — two identical trend methods

`get_event_trend()` and `get_metric_trend()` were functionally identical.
Both built the same `reports` POST body, parsed the same row structure,
treated non-numeric API values (e.g. `"N/A"`) as 0, and computed the same statistics dict.
The only difference was that `get_event_trend` added a `"metrics/"` prefix
to the event ID before making the call.

Any bug fix or API change to the trend logic required editing both methods.

### 2. `cache.py` — duplicated expiry logic

The legacy fallback branch in `_is_key_expired()` (used when per-key metadata
is absent) contained 5 lines that manually replicated the exact logic already
implemented in `_is_expired()`:

```python
created_str = metadata.get('created')
if not created_str:
    return True
try:
    created = datetime.fromisoformat(created_str)
    return (datetime.now() - created).total_seconds() > 3600
except (ValueError, TypeError):
    return True
```

### 3. `main.py` — listing and export routes duplicating data-building logic

For `core`, `props`, and `evars`, the listing route and its matching CSV
export route each contained identical filtering, transformation, and sorting
logic.  If the filter criteria changed (e.g. a new classification exclusion
rule), the change had to be made in two places.

---

## Solution

### 1. Extract `_fetch_trend_data()` in `adobe_analytics_v2.py`

Added a private `_fetch_trend_data(rsid, metric_id, days)` method containing
the shared implementation.  Both `get_event_trend()` and `get_metric_trend()`
now normalise their metric ID and delegate:

```python
def get_event_trend(self, rsid, event_id, days=30):
    if not event_id.startswith("metrics/"):
        event_id = f"metrics/{event_id}"
    return self._fetch_trend_data(rsid, event_id, days)

def get_metric_trend(self, rsid, metric_id, days=30):
    return self._fetch_trend_data(rsid, metric_id, days)
```

### 2. Simplify `_is_key_expired()` fallback in `cache.py`

The 5-line legacy fallback was replaced with a single call to the existing
`_is_expired()` method, which does exactly the same thing:

```python
if not key_meta:
    return self._is_expired(cache_name)
```

### 3. Extract data helpers in `main.py`

Added three module-level helpers — `_get_core_data()`, `_get_props_data()`,
and `_get_evars_data()` — each taking `(api, rsid)` and returning the
transformed, sorted list of rows.  The listing and export routes now each
reduce to two lines:

```python
@main_bp.route('/<client>/props')
def props():
    data = _get_props_data(get_api_service(), get_rsid())
    return render_listing('Props', data, list(PROPS_COLUMNS.values()), 'props', cache_key='dimensions')

@main_bp.route('/<client>/props/export')
def props_export():
    data = _get_props_data(get_api_service(), get_rsid())
    return generate_csv(data, f'{get_rsid()}_props.csv')
```

The nested `sort_key` function duplicated between `core()` and `core_export()`
was also removed and replaced with a module-scoped `_core_sort_key` defined
just above `_get_core_data()`.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | Added `_fetch_trend_data()`; simplified `get_event_trend()` and `get_metric_trend()` |
| `app/services/cache.py` | `_is_key_expired()` legacy fallback → single `_is_expired()` call |
| `app/routes/main.py` | Added `_get_core_data()`, `_get_props_data()`, `_get_evars_data()`; simplified 6 routes |
| `docs/autopsies/062-refactor-reduce-duplication.md` | This document |

---

## Tests

All 131 existing tests pass without modification.  No logic was changed, only
structure — existing test coverage validates the refactored code paths.
