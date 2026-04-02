# 044 — Listing Page UX Improvements

**Date:** 2026-04-02
**Branch:** `feature/listing-page-improvements`
**Status:** Complete

---

## Problem

Three linked UX complaints against the DataTables listing pages (Props, eVars, Events, ListVars, Segments, Metrics, etc.):

1. **Striped rows too prominent** — the default Bootstrap `table-striped` shade (`rgba(0,0,0,0.05)`) produced a noticeable grey band; the todo asked for it to be halved.
2. **Column headers scroll away** — on long tables users had to scroll back to the top to recall what each column meant.
3. **Wasted toolbar row** — the ↺ Refresh link sat alone in a row above the table while Copy / ColVis / Download sat in a second row; merging them saves vertical space.

---

## Solution

### 1. Lighter striped rows — `base.html`

Bootstrap 5 computes the stripe colour through the CSS custom property `--bs-table-bg`, which is set to `var(--bs-table-striped-bg)` on odd rows. Overriding `--bs-table-bg` directly for those rows is the most reliable way to reduce intensity without touching Bootstrap's own variables:

```css
.table-striped > tbody > tr:nth-of-type(odd) > * {
    --bs-table-bg: rgba(0, 0, 0, 0.025);
}
```

`0.025` is exactly half the Bootstrap default of `0.05`. This rule is in `base.html` so it applies to every listing page in the app.

### 2. Sticky column headers — `base.html`

The fixed navbar occupies `56px` at the top of the viewport (matching `body { padding-top: 56px }`). The app-title bar below it is _not_ fixed — it scrolls away. So the correct sticky offset is `top: 56px`:

```css
#dataTable thead th {
    position: sticky;
    top: 56px;
    z-index: 2;
    background-color: #fff;
    box-shadow: 0 1px 0 #dee2e6;
}
```

Selecting by `#dataTable` keeps this rule scoped to listing pages. The solid white background prevents table rows from bleeding through behind the headers as they scroll. A subtle `box-shadow` replaces the border that `position: sticky` removes from the header row.

No additional DataTables plugin is needed — with `paging: false` and no `scrollY` configured, DataTables renders a standard `<table>` and CSS sticky works directly.

### 3. Refresh button in toolbar — `listing.html`

The separate `<a>` element above the table was removed. In its place, a custom DataTables button is conditionally added when `cache_key` is set:

```js
{% if cache_key %}
{
    text: '&#x21ba; Refresh',
    className: 'btn-outline-secondary',
    titleAttr: 'Force refresh data from API',
    action: function() { window.location.href = '/cache/refresh/{{ cache_key }}'; }
},
{% endif %}
```

The button appears first in the row so it reads: **↺ Refresh | Copy | Column visibility | Download ▾** — all on a single line above the filter and table.

---

## Changes

| File | Change |
|------|--------|
| `app/templates/base.html` | Added CSS: lighter stripe, sticky `#dataTable thead th` |
| `app/templates/listing.html` | Removed standalone Refresh div; added custom Refresh button to DataTables |
| `docs/todo.md` | Marked all three listing improvement items as done |

---

## Notes

- The sticky offset (`56px`) is hardcoded to match `body { padding-top: 56px }`. If the navbar height ever changes, both values must be updated together.
- The `btn-outline-secondary` className on the custom button gives it a lighter border style compared to the filled-grey Copy/Download buttons, matching the original Refresh button's appearance.
- Pages that do not have a `cache_key` (e.g. Core Dimensions) continue to work correctly — the Refresh button simply does not appear.
