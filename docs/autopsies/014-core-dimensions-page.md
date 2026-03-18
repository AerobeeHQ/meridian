# 014 - Core Dimensions Page

**Date:** March 18, 2026
**Status:** Completed

## Summary

Added a new "Core" page to display out-of-the-box Adobe Analytics dimensions (Page Name, Channel, Product, Links, etc.) with the same functionality as Props/eVars pages including listing, export, and detail views.

## Problem Statement

The application displayed custom dimensions (Props, eVars, Events, ListVars) but was missing core/standard Adobe Analytics dimensions that are available out-of-the-box in every report suite. Users needed visibility into these fundamental tracking dimensions.

## Changes Made

### Files Modified

1. **`app/routes/main.py`**
   - Added `CORE_COLUMNS` mapping for display columns
   - Defined `CORE_DIMENSION_IDS` list with 12 core dimensions:
     - Page Name (`variables/page`)
     - Page URL (`variables/pageurl`)
     - Site Section (`variables/sitesection`)
     - Server (`variables/server`)
     - Channel (`variables/channel`)
     - Custom Link (`variables/customlink`)
     - Download Link (`variables/downloadlink`)
     - Exit Link (`variables/exitlink`)
     - Product (`variables/product`)
     - Referring Domain (`variables/referrer`)
     - Campaign (`variables/campaign`)
     - Search Engine (`variables/searchengine`)
   - Added `@main_bp.route('/core')` - Core dimensions listing page
   - Added `@main_bp.route('/core/export')` - CSV export functionality
   - Added `@main_bp.route('/core/<dimension_id>')` - Individual dimension detail pages

2. **`app/templates/base.html`**
   - Added "Core" navigation menu item before "Props" (lines 176-178)
   - Added active tab highlighting for `active_tab='core'`

3. **`app/templates/table.html`**
   - Added support for clickable "Dimension" column links when `active_tab == 'core'`
   - Core dimension IDs link to `/core/<dimension_id>` detail pages

## Technical Implementation

### Architecture Pattern
Followed the existing pattern established by Props/eVars pages:
- **Data Source:** Uses API 2.0 `GET /dimensions` endpoint
- **Filtering:** Filters raw dimensions by matching against `CORE_DIMENSION_IDS` list
- **Caching:** Leverages existing `get_cached_data()` infrastructure
- **Detail Pages:** Reuses existing `detail.html` template
- **Export:** Follows same CSV generation pattern

### Core Dimensions Detection
```python
# Filter core dimensions from all dimensions
for dim in raw_dimensions:
    dim_id = dim.get("id", "")
    if dim_id in CORE_DIMENSION_IDS:
        # Transform and add to results
```

### Sorting Strategy
Dimensions are sorted by their position in `CORE_DIMENSION_IDS` list rather than alphabetically, ensuring logical grouping:
1. Page-related dimensions (page, pageurl, sitesection, server)
2. Navigation dimensions (channel, links)
3. Commerce dimensions (product)
4. Traffic source dimensions (referrer, campaign, searchengine)

## Feature Completeness

✅ **Implemented:**
- Core dimensions listing page at `/core`
- CSV export functionality
- Detail pages for each core dimension with:
  - Configuration table
  - Top 10 items (last 30 days)
  - 30-day trend chart with statistics
  - Classifications (if any exist)
- Navigation menu integration (positioned before Props)
- Consistent UI/UX with existing pages
- Full caching support
- Parallel API calls for detail pages

## API Usage

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/dimensions` | GET | Get all dimensions (filtered for core dimensions) |
| `/reports` | POST | Get top items for detail pages |
| `/reports` | POST | Get trend data for detail pages |

## Code Quality Improvements

During implementation, two high-priority code issues were identified and fixed:

### 1. Median Calculation Bug (High Priority) ✅
**File:** `app/services/adobe_analytics_v2.py`

**Problem:** Manual median calculation was incorrect for even-length lists:
```python
# BEFORE (incorrect)
"median": round(sorted(numeric_values)[len(numeric_values) // 2], 1)
```

**Solution:** Use `statistics.median()` for correct calculation:
```python
# AFTER (correct)
import statistics
"median": round(statistics.median(numeric_values), 1)
```

**Impact:** Chart statistics now show accurate median values for all detail pages.

### 2. Dimension ID Parsing Error Handling (High Priority) ✅
**File:** `app/routes/main.py`

**Problem:** Dimension ID parsing could fail with `ValueError` on malformed IDs:
```python
# BEFORE (unsafe)
options[2:] = sorted(options[2:], key=lambda x: int(x['id'].replace('prop', '') or 0))
```

**Solution:** Added safe extraction helper function:
```python
def safe_extract_dimension_number(dim_id: str, prefix: str) -> int:
    """
    Safely extract numeric suffix from a dimension ID.
    Returns 999 if parsing fails (sorts to end).
    """
    try:
        cleaned = dim_id.replace(prefix, '')
        return int(cleaned) if cleaned else 999
    except (ValueError, AttributeError):
        return 999

# Usage
options[2:] = sorted(options[2:], key=lambda x: safe_extract_dimension_number(x['id'], 'prop'))
```

**Impact:** Notes API dropdowns are now resilient to malformed dimension IDs across all dimension types (props, evars, events, listvars).

## Testing

✅ **Manual Testing:**
- Core listing page loads (HTTP 200)
- All 12 core dimensions display correctly
- CSV export generates valid file
- Detail pages render with correct data
- Navigation highlighting works
- Caching reduces subsequent loads to <0.1s
- Classifications display when present
- Error handling prevents crashes on malformed data

✅ **Regression Testing:**
- Existing Props/eVars/Events pages unaffected
- Navigation menu renders correctly
- Detail page templates work for all dimension types

## Performance

| Scenario | Load Time |
|----------|-----------|
| Core listing (first load) | ~2-3s (API call) |
| Core listing (cached) | <0.1s |
| Core detail (after listing) | ~2.5s (parallel API calls) |
| Core detail (cached) | <0.05s |

Performance follows same pattern as Props/eVars due to shared caching and parallel fetch infrastructure.

## Files Changed

| File | Lines Changed | Action |
|------|---------------|--------|
| `app/routes/main.py` | +180 | Added core routes, CORE_COLUMNS, CORE_DIMENSION_IDS, safe parsing helper |
| `app/templates/base.html` | +3 | Added Core navigation menu item |
| `app/templates/table.html` | +2 | Added Dimension column link support |
| `app/services/adobe_analytics_v2.py` | +1, ~2 | Fixed median calculation bug |

**Total:** ~186 lines added, ~2 lines modified

## Future Enhancements

Potential improvements for consideration:
- [ ] Allow users to customize which core dimensions are displayed
- [ ] Add more core dimensions (geo, device, OS, browser, etc.)
- [ ] Group dimensions by category in the UI
- [ ] Add dimension status indicators (enabled/disabled)

---

**Lessons Learned:**

1. **Code Reuse:** Following established patterns (Props/eVars) made implementation straightforward
2. **Error Handling:** Proactive error handling prevents runtime failures on unexpected data
3. **Statistics Functions:** Use standard library functions (`statistics.median`) instead of manual calculations
4. **Documentation:** Swagger API documentation confirmed all standard dimensions are available via same endpoint

