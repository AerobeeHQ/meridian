# Plan: Marketing Channel Rules Integration on Detail Pages

**Roadmap item:** When viewing a Prop, eVar, Event, or ListVar, show which Marketing Channel Processing Rules set or alter that dimension.

**Complexity: Medium**

---

## Overview

Very similar pattern to the Processing Rules integration (v2-001). Marketing channel rules data is already fetched and cached via `get_marketing_channel_rules()` in `adobe_analytics.py`. The work is to cross-reference channel rule conditions and actions against the current dimension on detail pages.

---

## Current State

- `GET /channel-rules` fetches and caches all channel rules (API 1.4 only).
- Each rule has channel, conditions, and match attributes.
- The rules are separate from processing rules — they classify traffic into marketing channels, not set custom variables.
- Detail pages have no reference to channel rules.

---

## Implementation Plan

### Step 1 — Understand the data shape

Review the channel rules response from `get_marketing_channel_rules()` to confirm field names and structure before implementing matching logic. Key fields to identify:
- Condition fields that reference eVars, props, events, or query string params
- Any field that maps back to a custom variable

**Note:** Marketing channel rules primarily match on referrer, URL patterns, and query parameters — they rarely directly reference eVars or props in conditions. The more common case is that a channel rule *writes to* a marketing channel eVar (typically eVar0/channel). Check the actual API response to confirm what's useful to surface.

### Step 2 — Helper: find matching channel rules for a dimension

Add a `find_related_channel_rules()` helper (alongside the processing rules helper from v2-001):

1. Accepts the cached channel rules list and a dimension identifier.
2. Searches condition strings for the dimension name using the same matching strategy as v2-001.
3. Returns matching rule dicts with channel name, conditions, and match type.

If the API response shows channel rules do not reference custom variables in their conditions, the scope of this feature may be narrower than v2-001 — it may only be relevant for the marketing channel eVar itself. Confirm before implementing.

### Step 3 — Load channel rules in detail page routes

Same pattern as v2-001:

1. Load cached channel rules: `cache.get_or_set(rsid, 'channel_rules', fetch_fn)`.
2. Call `find_related_channel_rules()`.
3. Pass `related_channel_rules` to template context.

### Step 4 — Template: add "Related Channel Rules" section

In `detail.html`, `event_detail.html`, and `listvar_detail.html`:

- Add a collapsible section after the Processing Rules section (from v2-001).
- Show channel name, match type, and conditions for each related rule.
- If none, show "No marketing channel rules reference this dimension."

---

## Files to Change

| File | Change |
|------|--------|
| `app/routes/main.py` | Add `find_related_channel_rules()` helper; call it in each detail route |
| `app/templates/detail.html` | Add Related Channel Rules section |
| `app/templates/event_detail.html` | Add Related Channel Rules section |
| `app/templates/listvar_detail.html` | Add Related Channel Rules section |

---

## Risks & Notes

- **Depends on v2-001:** Implement after v2-001 since the pattern is identical — much of the code can be reused.
- **Data inspection required first:** Marketing channel rules may not reference custom variables in a way that makes cross-linking useful. Inspect a real API response before committing to this feature's scope.
- **No API changes needed** — channel rules are already cached.
