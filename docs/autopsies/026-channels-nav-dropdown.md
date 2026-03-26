# 026 — Channels Nav Dropdown

**Date:** March 26, 2026
**Status:** Completed
**Branch:** `feature/channels-nav-dropdown`

## Problem

The global navigation had nine top-level items — Core, Props, eVars, Events, ListVars, Proc Rules, Marketing Channels, Channel Rules, Segments — plus the More dropdown. "Marketing Channels" and "Channel Rules" are two views of the same feature area and took up two nav slots. With Segments now added the bar was getting crowded, and on smaller viewports it collapsed earlier than ideal.

## Fix

Replaced the two separate nav items with a single **Channels** dropdown containing both links. A section header ("Marketing Channels") gives the dropdown context. The existing page is renamed "Channel Setup" inside the dropdown to be more descriptive, while keeping the URL and `active_tab` value unchanged.

### Active-state highlighting

The dropdown toggle gains the `active` class whenever `active_tab` is `'marketing-channels'` or `'channel-rules'`. Each dropdown item also gets its own `active` class for the currently selected page — consistent with how Bootstrap 5 styles active dropdown items.

## Before / After

**Before (9 top-level items):**
```
Core | Props | eVars | Events | ListVars | Proc Rules | Marketing Channels | Channel Rules | Segments | More ▾
```

**After (8 top-level items):**
```
Core | Props | eVars | Events | ListVars | Proc Rules | Channels ▾ | Segments | More ▾
```

Channels dropdown:
```
Marketing Channels
  Channel Setup      → /marketing-channels
  Channel Rules      → /channel-rules
```

## Files Changed

| File | Change |
|------|--------|
| `app/templates/base.html` | Replaced two `<li>` nav items with a single dropdown `<li>` |

No route, service, or cache changes were needed.
