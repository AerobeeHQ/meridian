# 018 — eVar Listing: Expiration & Allocation Display

**Date:** March 25, 2026
**Status:** Completed

## Summary

Added human-readable Expiration and Allocation values to the eVars listing page (`/evars`). Previously these columns existed in the table but showed raw internal keys (e.g., `purchase_event` instead of "Purchase Event"). Now the listing page displays the same friendly labels as the detail page.

## Problem Statement

The eVars listing page defined Expiration and Allocation columns in `EVARS_COLUMNS`, and the `_transform_dimension_to_evar()` method populated them via `parse_description_metadata()` (added in autopsy 017). However, the values were raw internal identifiers:

- `purchase_event` instead of "Purchase Event"
- `hit` instead of "Hit"
- `never` instead of "Never"

An outdated code comment (from before autopsy 017) incorrectly stated these columns "will be empty in the table view", which may have delayed noticing the issue.

## Solution

Added two formatting helpers in `app/routes/main.py`:

- **`format_expiration(expiration_type, custom_days)`** — Maps internal keys (`purchase_event`, `hit`, `visit`, etc.) to human-readable labels. Handles custom-day formats (e.g., `custom` + `30` → "30 Days").
- **`format_allocation(allocation_type)`** — Maps snake_case keys (`most_recent_last`, `merchandising_last`, etc.) to labels. Passes through raw text from API 2.0 descriptions that are already human-readable.

Applied formatting in both the `/evars` listing route and `/evars/export` CSV route so exports match the UI.

## Files Changed

- `app/routes/main.py` — Added `format_expiration()` and `format_allocation()` helpers; applied formatting in `evars()` and `evars_export()` routes; removed outdated comment about empty columns
- `docs/todo.md` — Marked allocation/expiration listing item as done; marked merchandising eVar bug as done (fixed in PR #26)

## Why This Approach

- **Route-level formatting:** Keeps the service layer returning canonical keys (useful for detail page template logic) while the route layer formats for display. No changes to `adobe_analytics_v2.py` or `detail.html`.
- **API 2.0 only:** Relies entirely on `parse_description_metadata()` which extracts data from API 2.0 description fields — no API 1.4 dependency for listing pages.
- **Consistent labels:** The formatting maps mirror the Jinja2 conditionals in `detail.html`, ensuring listing and detail pages show identical labels.

## Testing

1. Run `uv run run.py` and navigate to `/evars`
2. Verify Expiration column shows labels like "Hit", "Visit", "Purchase Event", "Never", "30 Days"
3. Verify Allocation column shows labels like "Most Recent (Last)", "Merchandising (Last)"
4. Verify eVar detail pages still display correctly (unchanged code path)
5. Export CSV from `/evars/export` and confirm formatted values in the file
