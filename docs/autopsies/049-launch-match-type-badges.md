# 049 — Launch Panel: Match Type Badges

**Date:** 2026-04-03
**Branch:** `feature/launch-match-type-badges`
**Status:** Complete

---

## Problem

The Adobe Launch panel on dimension detail pages showed each matched rule with a raw `delegate_descriptor_id` hint (e.g. `adobe-analytics::actions::setVariables`) in a monospace footnote. Two problems:

1. **No visual distinction** between match types. An "Action" that sets a variable looks identical to a "Condition" that reads one, or an "Event" that fires when it changes.

2. **Silent false positives.** The Reactor `/search` API uses `attributes.*` (full-text across all attribute fields), so a rule whose *name* happens to contain the dimension string (e.g. "Clear eVar1 on exit") appears in results even if none of its components set that variable. These name-only matches had no visual indicator to distinguish them from genuine settings references. This was noted as an accepted risk in [autopsy 040](040-launch-search-api-refactor.md).

---

## Solution

Updated the `related_launch_rules_section` macro in `_macros.html` to parse `delegate_descriptor_id` inline and surface three new pieces of information per entry.

### 1. Component type badge

The `delegate_descriptor_id` format is `{extension}::{component_type}::{name}`, where `component_type` is one of `actions`, `conditions`, or `events`. The macro splits on `::` and renders a coloured badge:

| `component_type` | Badge | Colour |
|-----------------|-------|--------|
| `actions` | **Action** | Green subtle |
| `conditions` | **Condition** | Blue subtle |
| `events` | **Event** | Info subtle |

### 2. "Name match" indicator

When a rule entry has **no** `delegate_descriptor_id` it matched the search only through its name or description — not through any component's settings. These entries now show a grey **Name match** badge with a tooltip explaining the caveat:

> "This rule appeared because its name or description contains the dimension string. It may not directly set this variable."

### 3. Human-readable action label

The raw `delegate_descriptor_id` string is still shown (in small muted monospace, for debugging), but a clean label now appears alongside it:

| `delegate_name` | Label |
|----------------|-------|
| `setVariables` | Sets Analytics Variables |
| `sendBeacon` | Sends Analytics Beacon |
| `custom-code` | Custom Code |
| `variable` | Variable |
| *(other)* | Title-cased, hyphens replaced with spaces |

### Disabled badge colour

Upgraded the "Disabled" badge from plain `bg-secondary` to `bg-danger-subtle text-danger-emphasis` for better visibility — consistent with Bootstrap 5 contextual colour conventions.

---

## Before / After

**Before:**
```
[Rule name link]                        [Disabled]
  adobe-analytics::actions::setVariables
```

**After:**
```
[Rule name link]  [Action]              [Disabled]
  Sets Analytics Variables  (adobe-analytics::actions::setVariables)

[Rule name link]  [Name match]
  (no action label — matched by rule name only)
```

---

## Files Changed

| File | Change |
|------|--------|
| `app/templates/_macros.html` | `related_launch_rules_section` macro — parse `delegate_descriptor_id`; add component type badge; add "Name match" badge; add readable action label; improve Disabled badge colour |

---

## Notes

- No backend changes — all parsing is done in Jinja2 within the macro.
- The raw `delegate_descriptor_id` is retained in the UI (small, muted) so developers can still see the exact delegate type for debugging.
- The "Name match" badge does not remove these entries — they may still be relevant (e.g. a rule named "Set eVar1 from data layer" where the actual value comes from a data element). The badge prompts the user to verify rather than hiding the result.
