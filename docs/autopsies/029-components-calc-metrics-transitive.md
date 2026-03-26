# 029 — Fix: Components Panel Missing Calculated Metrics for Props and eVars

**Date:** 2026-03-26
**Branch:** `fix/components-calc-metrics-transitive`
**Status:** Complete

---

## Bug

After shipping the Components panel (PR #38 / autopsy 028), the panel correctly showed segments that reference a prop or eVar, but showed **zero calculated metrics** for those same dimensions — even when calculated metrics clearly depended on them.

Events worked fine: visiting an Event detail page showed both segments and calculated metrics that referenced that event.

---

## Root Cause

The difference comes down to how Adobe Analytics formula JSON is structured:

**Events in a calculated metric** — referenced *directly* in the formula tree:
```json
{ "func": "metric", "name": "metrics/event1" }
```

**Props/eVars in a calculated metric** — *never* referenced directly. A calculated metric filters by a segment; the segment definition contains the variable reference:
```json
// Calculated metric formula:
{ "func": "metric", "name": "metrics/visits",
  "filters": [{ "func": "segment-ref", "id": "s123_abc456" }] }

// Segment s123_abc456 definition:
{ "func": "attr", "name": "variables/evar5", ... }
```

The original `_find_components()` did a single pass searching for `"variables/evar5"` in each calculated metric's definition JSON — which never matches, because that string only appears inside the *segment's* definition, not the CM's.

---

## Fix

Two-pass lookup in `_find_components()`:

1. **Pass 1** (unchanged): Find segments whose definitions contain the variable ID. Collect their IDs into a set.

2. **Pass 2** (new): For each calculated metric, check:
   - **(a) Direct reference**: the variable ID appears in the CM definition (covers events)
   - **(b) Transitive reference**: any of the matched segment IDs appear in the CM definition (covers props/evars via `segment-ref` nodes)

```python
# Pass 2 – direct OR transitive
definition_str = json.dumps(definition)
direct    = needle in definition_str
transitive = any(f'"{seg_id}"' in definition_str for seg_id in matched_segment_ids)
if direct or transitive:
    matching_metrics.append(...)
```

The transitive check works because segment IDs are unique opaque strings (e.g. `s300000123_abc123def456`) and their quoted form is unambiguous inside any JSON.

---

## Files Changed

| File | Change |
|------|--------|
| `app/routes/main.py` | Rewrote `_find_components()` with two-pass segment-transitive lookup |
| `docs/todo.md` | Marked bug as fixed |

---

## Notes

- No API changes required — the `definition` fields added in PR #38 already contain all the data needed for the transitive lookup
- The fix is purely in the Python search logic; no template changes
- If a calculated metric references the variable *both* directly and through a segment, it still appears exactly once (no deduplication needed — the `if direct or transitive` short-circuits correctly)
