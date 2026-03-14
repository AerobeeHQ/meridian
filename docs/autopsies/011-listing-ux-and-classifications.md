# 011 - Listing Page UX Improvements and Classifications

## Date
March 14, 2026

## Summary
Improved the UX of the listing page with row highlighting features and filtered out classified variables from the main listing, displaying them on parent variable detail pages instead.

## Changes Made

### 1. Row Hover Highlight (base.html)
Added CSS to highlight table rows on hover:
```css
.table-hover tbody tr:hover {
    --bs-table-bg: #EFF4FA !important;
}
```

### 2. Click-to-Select Row Highlighting (base.html)
- Added `.selected` CSS class with darker blue background (`#d4e5f7`)
- Added JavaScript click handler that:
  - Toggles row selection on click
  - Only allows one selected row at a time
  - Ignores clicks on links (so navigation still works)
  - State is not persisted across page reloads

### 3. Subtle Link Styling (base.html)
Styled Prop/eVar detail links to be less prominent than traditional hyperlinks:
- No underline
- Medium font weight (500)
- Subtle blue color (#2c5282)
- Rounded background on hover
- White text when row is selected

### 4. Classifications Hidden from Listing Pages (main.py)
Modified `props()`, `props_export()`, `evars()`, and `evars_export()` routes to filter out classified variables:
- Classifications are identified by having a `.` in the ID (e.g., `prop12.screen-height`)
- Only parent variables (e.g., `prop12`) appear in listings

### 5. Classifications Shown on Detail Pages (main.py, detail.html)
- Updated `prop_detail()` and `evar_detail()` to find classifications by matching the `parent` field
- Added classifications section to detail.html template
- Classifications are displayed as clickable links to their own detail pages
- Sorted alphabetically by name

## Files Modified
- `app/templates/base.html` - CSS styles and JavaScript for row highlighting
- `app/routes/main.py` - Filtering logic and classifications data
- `app/templates/detail.html` - Classifications section in detail view

## Testing
- Manual testing: Run `uv run run.py` and verify:
  1. Rows highlight on hover (light blue)
  2. Clicking a row selects it (darker blue), clicking again deselects
  3. Links turn white when row is selected
  4. Classifications don't appear in Props/eVars listings
  5. Classifications appear on parent variable detail pages
  6. Clicking a classification navigates to its detail page

