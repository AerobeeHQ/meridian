# Autopsy 041 — Hide Rule Panels for Classified Dimensions

**Date:** 2026-03-31
**Branch:** `fix/hide-panels-for-classified-dimensions`
**Status:** Complete — pending commit

---

## Problem

When viewing a classified dimension (e.g. `/evars/evar8.suburb`), the detail page made AJAX calls for three panels that can never have results:

- **Related Processing Rules** — the API has no concept of setting a classification via a processing rule
- **Adobe Launch** — Launch rules set the parent variable (`eVar8`), not a sub-classification
- **Related Channel Rules** — same as processing rules

Each panel would load, make an API call or cache lookup, and render an empty "No rules reference this dimension" message — adding noise and unnecessary requests to every classified dimension page.

---

## Fix

Added a two-line early return to each of the three fragment endpoints in `app/routes/main.py`:

```python
if '.' in dimension_id:
    return '', 204
```

The existing JavaScript on the detail page already handles 204 correctly for the Launch panel (removes the placeholder without error). The Processing Rules and Channel Rules panels use the same `then(r => r.text())` pattern — a 204 response resolves to empty text, `insertAdjacentHTML` inserts nothing, and `placeholder.remove()` silently removes the card. No template changes required.

The **Components** panel (segments and calculated metrics that reference the dimension) is intentionally left unchanged — a segment _can_ legitimately reference a classified dimension, so that panel still makes sense.

---

## Why at the Route Level

The check could have been done in the template (skip the AJAX call when `'.' in dimension_id`). Doing it at the route level is preferable because:

1. Consistent with the existing pattern — Launch already returns 204 for disabled state at the route level.
2. No business logic in templates.
3. Correctly handles any client that calls the endpoints directly (e.g. the debug page).

---

## Files Changed

| File | Change |
|------|--------|
| `app/routes/main.py` | Added `if '.' in dimension_id: return '', 204` guard to `api_related_rules`, `api_related_launch_rules`, and `api_related_channel_rules` |
