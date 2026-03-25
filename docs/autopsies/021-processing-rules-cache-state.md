# 021 — Processing Rules: Distinguish Cold Cache from Empty Result

**Date:** March 25, 2026
**Status:** Completed
**Branch:** `fix/processing-rules-cache-state`
**Depends on:** Feature branch `feature/processing-rules-on-detail-pages` (autopsy 020)

## Problem

After autopsy 020 added the "Related Processing Rules" section to detail pages, both of these states looked identical to the user:

1. **Cache cold** — the `processing_rules` key is absent from the cache because the `/processing-rules` page hasn't been visited yet, or API 1.4 was unavailable when it was last attempted.
2. **Genuinely no matches** — the cache was populated and searched, but this dimension isn't referenced by any rules.

In both cases the section showed: *"No processing rules reference this dimension."*

This is misleading in state (1). An analyst could easily conclude there are no relevant rules when in fact the data simply hasn't been loaded — or the API was temporarily down.

## Root Cause

The original route code collapsed the distinction immediately:

```python
cached_rules = cache.get(rsid, 'processing_rules') or []
```

`cache.get()` returns `None` on a cache miss and the stored value (a list, possibly empty) on a hit. The `or []` coercion silently equated both states before any availability check could be made.

## Fix

**Routes (`app/routes/main.py`)** — all four detail routes (`prop_detail`, `evar_detail`, `event_detail`, `listvar_detail`) now preserve the raw cache result before collapsing it:

```python
_cached_rules_raw = cache.get(rsid, 'processing_rules')
processing_rules_cached = _cached_rules_raw is not None   # None = cold cache
related_rules = find_related_processing_rules(_cached_rules_raw or [], ...)
```

`processing_rules_cached` (a bool) is passed to the template.

**Macro (`app/templates/_macros.html`)** — `related_processing_rules_section` gains a second parameter `rules_available` (defaults to `true` for backward compatibility):

```jinja
{% macro related_processing_rules_section(related_rules, rules_available=true) %}
```

Three rendering states are now handled distinctly:

| State | `rules_available` | `related_rules` | UI |
|---|---|---|---|
| Cache cold / API down | `false` | `[]` | ⚠️ amber warning banner with "Load Processing Rules" link |
| Cache warm, no matches | `true` | `[]` | Muted "No processing rules reference this dimension." |
| Cache warm, matches found | `true` | `[…]` | Bootstrap accordion listing each rule |

**Templates** — all three call sites updated to pass the availability flag:

```jinja
{{ related_processing_rules_section(
    related_rules | default([]),
    processing_rules_cached | default(false)
) }}
```

The `| default(false)` guard means if `processing_rules_cached` is somehow absent from the template context, the macro degrades to the warning state rather than falsely claiming no rules exist.

## Why This Matters

API 1.4 can go down for hours at a time. Without this fix, every detail page visited during an outage would silently show "No processing rules reference this dimension" — even for heavily-instrumented variables with dozens of rules. The amber warning banner makes the data gap visible and gives the analyst a clear recovery action.

## Files Changed

- `app/routes/main.py` — four detail routes updated to capture and pass `processing_rules_cached`
- `app/templates/_macros.html` — `related_processing_rules_section` macro updated with `rules_available` parameter and three-state rendering
- `app/templates/detail.html` — macro call updated
- `app/templates/event_detail.html` — macro call updated
- `app/templates/listvar_detail.html` — macro call updated

## Testing

**Cold cache state:** Clear the processing rules cache key (or test before visiting `/processing-rules`) and load any dimension detail page. Verify the amber "Processing rules data is not available" banner appears with the "Load Processing Rules" button.

**Warm cache, no matches:** Load `/processing-rules` to populate the cache, then visit a dimension that isn't referenced by any rule. Verify the muted "No processing rules reference this dimension." message appears.

**Warm cache, with matches:** Visit a dimension that is referenced. Verify the accordion renders correctly.
