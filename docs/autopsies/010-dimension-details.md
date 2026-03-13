# Autopsy: Dimension Details View Feature

**Issue:** Implement dimension detail pages for props and eVars
**Date:** March 13, 2026
**Status:** Completed

## Summary

Implemented clickable detail pages for Traffic Variables (props) and Conversion Variables (eVars) that show dimension configuration, top 10 recorded values, and a 30-day trend chart with summary statistics.

## Changes Made

### Files Created
- `app/templates/detail.html` - Detail page template with configuration table, top values table, Chart.js trend chart, and summary statistics

### Files Modified

1. **`app/services/adobe_analytics_v2.py`**
   - Added `datetime` and `timedelta` imports
   - Added `get_dimension(rsid, dimension_id)` - Retrieves single dimension by filtering from dimensions list
   - Added `get_top_items(rsid, dimension, metric, limit, days)` - Uses POST /reports endpoint to get top values
   - Added `get_dimension_trend(rsid, dimension, metric, days)` - Gets daily time-series data for trend chart

2. **`app/routes/main.py`**
   - Added `/props/<prop_id>` route for prop detail pages
   - Added `/evars/<evar_id>` route for eVar detail pages

3. **`app/templates/table.html`**
   - Made Prop and eVar ID columns clickable links to detail pages

4. **`app/templates/base.html`**
   - Added `dimension_id` to breadcrumb when on detail pages

### Documentation
- Updated `.docs/details-view.md` implementation checklist

## Technical Notes

### Issue 1: Single Dimension Endpoint (404)
**Problem:** The `GET /dimensions/{id}` endpoint returned 404 for props (e.g., `dimensions/prop1`).
**Solution:** Changed `get_dimension()` to filter from the full dimensions list instead of using the single-dimension endpoint.

### Issue 2: TopItems Endpoint (403)
**Problem:** The `GET /reports/topItems` endpoint returned 403 Forbidden, likely due to API permissions.
**Solution:** Changed `get_top_items()` to use the `POST /reports` endpoint instead, which has broader permissions.

### Issue 3: DateRange Format (400)
**Problem:** The topItems endpoint required datetime format `yyyy-MM-dd'T'HH:mm:ss`, not just `yyyy-MM-dd`.
**Solution:** Updated date formatting to include time component: `2026-02-11T00:00:00/2026-03-13T23:59:59`

### Issue 4: Jinja2 Dict Key Collision
**Problem:** Template error "Object of type builtin_function_or_method is not JSON serializable" when accessing `trend_data.values`.
**Root Cause:** In Jinja2, `dict.values` accesses the dict's `.values()` method, not a key named `'values'`.
**Solution:** Changed dot notation to bracket notation: `trend_data['values']` instead of `trend_data.values`.

## API Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dimensions` | GET | Get all dimensions (filtered for single dimension) |
| `/reports` | POST | Get top items ranked report |
| `/reports` | POST | Get time-series trend data |

## Metrics Configuration

| Dimension Type | Metric Used |
|----------------|-------------|
| Props (Traffic Variables) | `occurrences` |
| eVars (Conversion Variables) | `instances` |

## Testing

- ✅ Props listing page loads (HTTP 200)
- ✅ Prop detail page loads (HTTP 200) - `/props/prop10`
- ✅ eVar detail page loads (HTTP 200) - `/evars/evar1`
- ✅ Configuration table renders with correct data
- ✅ Top values table renders with percentages and counts
- ✅ Chart.js trend visualization initializes
- ✅ Summary statistics display correctly
- ✅ Breadcrumb navigation works
- ✅ Back button navigates to listing

## Future Work

- [ ] Events detail page (similar pattern)
- [ ] ListVars detail page
- [ ] Marketing Channel detail page
- [ ] Date range selector (7/30/90 days)
- [ ] Export detail data as CSV

