# 050 — Launch Panel: Variable Assignments from setVariables Actions

**Date:** 2026-04-03
**Branch:** `feature/launch-variable-assignments`
**Status:** Complete

---

## Problem

The Adobe Launch panel on dimension detail pages showed which rules reference a dimension, but gave no detail about *what* value is being assigned. A rule using `adobe-analytics::actions::setVariables` to set `eVar1 → "logged_in"` and `eVar5 → %pageName%` was listed only as "Sets Analytics Variables" — the user had no way to see the actual assignments without opening the rule in Adobe Tags.

---

## Solution

### Backend — `_parse_set_variables_settings()`

Added a static method to `AdobeLaunchService` that parses the `settings` JSON string attached to a `setVariables` rule component. The settings blob follows the format:

```json
{
  "trackerProperties": {
    "evars":   {"evars":   [{"name": "eVar1",  "value": "logged_in"}]},
    "props":   {"props":   [{"name": "prop5",  "value": "%pageName%"}]},
    "events":  {"events":  [{"name": "event3", "value": ""}]}
  }
}
```

The method extracts all `name`/`value` pairs from evars, props, and events into a flat list of `{"variable": ..., "value": ...}` dicts. Returns an empty list if settings is absent or unparseable.

### Backend — `search_and_resolve()` aggregation

Changed `strategy_a` from a `rule_id → True` mapping to `rule_id → [comp_item, ...]` so all components for a rule are available. Added parallel `component_by_rule` and `component_by_comp` dicts (keyed by rule ID and component ID respectively).

When building each result entry, the method now loops over all `setVariables` components for the rule and aggregates their parsed assignments into a single `variable_assignments` list attached to the entry dict.

This correctly handles rules with multiple `setVariables` actions (e.g. one for eVars, one for events).

### Template — `related_launch_rules_section` macro

Added a `<ul>` below the action label that renders when `entry.variable_assignments` is non-empty:

```
Sets Analytics Variables  (adobe-analytics::actions::setVariables)
  eVar1  →  logged_in
  eVar5  →  %pageName%
  event3
```

Variable names and values are rendered in monospace. Values that are empty (event-only assignments with no value) show just the variable name. Data element tokens like `%pageName%` are displayed as-is.

---

## Before / After

**Before:**
```
[Set eVar1 on login]  [Action]
  Sets Analytics Variables  (adobe-analytics::actions::setVariables)
```

**After:**
```
[Set eVar1 on login]  [Action]
  Sets Analytics Variables  (adobe-analytics::actions::setVariables)
    eVar1  →  logged_in
    eVar5  →  %pageName%
    event3
```

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_launch.py` | Added `import json`; added `_parse_set_variables_settings()` static method; changed `strategy_a` to track component items; added `component_by_rule` / `component_by_comp` dicts; attached `variable_assignments` to each entry |
| `app/templates/_macros.html` | `related_launch_rules_section` macro — render `variable_assignments` list below action label |

---

## Notes

- Only `setVariables` components are parsed; `sendBeacon` and `custom-code` actions do not expose structured variable data in the same way.
- The `variable_assignments` field is always present on rule entries (`[]` when absent or not applicable), so the template `{% if entry.variable_assignments %}` guard is safe.
- Extensions and data elements are not affected — they have no `variable_assignments`.
