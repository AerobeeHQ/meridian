# 044 — Detail Page Panel Layout Reorganisation

**Date:** 2026-04-02
**Branch:** `feature/detail-page-panel-layout`
**Status:** Complete

---

## Problem

On all four dimension detail pages (prop/eVar, event, listVar), four async panels — **Related Processing Rules**, **Adobe Launch**, **Related Channel Rules**, and **Components** — sat in the **left column** below the config table. This created an awkward scroll experience: the left column was very long while the right column (trend chart + stats + Top 10 Values) was comparatively short.

The todo asked to:

1. Move those four panels to the **right column**, below the Top 10 Values table.
2. Rename **"Components"** → **"Segments & Calculated Metrics"**
3. Rename **"Related Channel Rules"** → **"Related Marketing Channel Rules"**
4. Rename **"Adobe Launch Rules"** → **"Adobe Launch"** (to match the macro card title)

---

## Solution

Pure template + macro change. No route or API changes.

### Before

```
Left column                    Right column
─────────────────              ─────────────────
Config table                   Trend chart
Related Processing Rules        Stats row
Adobe Launch Rules             Top 10 Values
Related Channel Rules
Components
Notes
```

### After

```
Left column                    Right column
─────────────────              ─────────────────
Config table                   Trend chart
Notes                          Stats row
                               Top 10 Values
                               Related Processing Rules
                               Adobe Launch
                               Related Marketing Channel Rules
                               Segments & Calculated Metrics
```

The left column is now compact (config + notes only). The right column shows the full data picture — live data first (trend, stats, top values), then context (what rules/segments reference this dimension).

---

## Changes

### `app/templates/_macros.html`

Updated two macro card titles at source so the change flows through to all pages:

| Old | New |
|-----|-----|
| `Components` | `Segments & Calculated Metrics` |
| `Related Channel Rules` | `Related Marketing Channel Rules` |

### `app/templates/detail.html` (props & eVars)

- Removed the four placeholder `<div>`s from the left column.
- Added them to the right column after the Top 10 Recorded Values card.
- Changed the Top 10 card from `class="card"` to `class="card mb-4"` to give consistent spacing before the panels.
- Updated spinner placeholder titles and JS error fallback strings to use the new names.

### `app/templates/event_detail.html`

- Same move: removed panels from left column (between Notes and the bottom of the left `col-md-6`), placed them at the bottom of the right column after the 30-Day Summary card.
- Updated placeholder and fallback titles.

### `app/templates/listvar_detail.html`

- Same move: right column, after Top 10 Values.
- Updated placeholder and fallback titles.

---

## Notes

- The async loading mechanism (JS `fetch` + `insertAdjacentHTML('afterend', ...)`) is position-agnostic: the panels replace their `<div id="...placeholder">` wherever it lives in the DOM. Moving the placeholder is sufficient to reposition the loaded panel.
- No JavaScript logic changed.
- No route or service changes.
