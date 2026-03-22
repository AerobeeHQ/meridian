# 016 - eVar Allocation and Expiration Display Fix

**Date:** March 18, 2026
**Status:** Completed

## Summary

Fixed a bug where eVar configuration fields (Allocation, Expiration, Enable Merchandising, and Merchandising syntax) were displaying as null/empty/undefined on the eVar detail pages, even though these values existed in the Adobe Analytics Admin Console.

## Problem Statement

When viewing eVar detail pages (e.g., `/evars/evar1`), the following configuration fields were showing as "N/A" or empty:
- **Allocation** (e.g., "Most Recent (Last)")
- **Expiration** (e.g., "Hit")
- **Enable Merchandising** (e.g., "Enabled")
- **Merchandising** (e.g., "Product Syntax")

These values were visible in the Adobe Analytics Admin Console but not in Codex.

## Root Cause

The Adobe Analytics API 2.0 `/dimensions` endpoint **does not include** eVar configuration details such as:
- `allocation_type`
- `expiration_type`
- `expiration_custom_days`
- `merchandising_syntax`
- `binding_events`

These fields are **only available** through the Adobe Analytics API 1.4 `ReportSuite.GetEvars` endpoint.

The eVar detail route was only fetching data from API 2.0, which provides basic dimension metadata (name, description, type) but not the detailed configuration settings.

### Investigation: API 2.0 Expansion Parameter

During troubleshooting, we discovered that API 2.0's `/dimensions` endpoint supports an `expansion` parameter with `attributionModel` as an option. However, testing revealed this does NOT solve the problem:

```python
# API 2.0 request with expansion
GET /dimensions/variables/evar1?rsid=xxx&expansion=attributionModel

# Response includes:
{
  "id": "variables/evar1",
  "name": "Product Location",
  "attributionModel": {
    "func": "allocation-instance"  // ← Not useful!
  },
  // ... other fields
}
```

**The `attributionModel` returned only contains `{"func": "allocation-instance"}`**, which:
- Does NOT specify the allocation type (Most Recent, Original Value, Linear, Merchandising, etc.)
- Does NOT include expiration settings
- Does NOT include merchandising syntax or binding events

**Conclusion:** API 2.0 has no endpoint that provides the detailed eVar configuration settings found in API 1.4's `ReportSuite.GetEvars`. The hybrid API approach is the correct solution.

### Additional Note: The `multiValued` Field

Further research revealed that API 2.0's `multiValued` field does NOT reliably indicate whether merchandising is enabled:
- **evar1**: `multiValued: false`, but has `merchandising_syntax: 'product'` and `allocation_type: 'merchandising_last'` → Merchandising IS enabled
- **evar6**: `multiValued: true`, but has `merchandising_syntax: None` and `allocation_type: 'most_recent_last'` → Merchandising is NOT enabled

The `multiValued` field appears to indicate something different (possibly related to list variables or multi-value delimiters). 

**The correct way to determine if merchandising is enabled is by checking if `allocation_type` contains "merchandising"** (`merchandising_last` or `merchandising_first`), which is only available from API 1.4.

## Solution

### 1. Added `get_evar()` Method to API 1.4 Service

**File:** `app/services/adobe_analytics.py`

Added a new method to fetch configuration for a single eVar by ID:

```python
def get_evar(self, rsid: str, evar_id: str) -> dict:
    """
    Get configuration for a single eVar
    
    Args:
        rsid: Report suite ID
        evar_id: eVar ID (e.g., 'evar1' or 'variables/evar1')
    
    Returns:
        eVar configuration dict with allocation, expiration, and merchandising settings
    """
    # Normalize evar_id to just the evar number (e.g., 'evar1')
    evar_id = evar_id.replace('variables/', '')
    
    # Get all evars and find the matching one
    evars = self.get_evars(rsid)
    for evar in evars:
        if evar.get('id') == evar_id:
            return evar
    
    return {}
```

### 2. Updated `evar_detail` Route to Fetch and Merge Configuration

**File:** `app/routes/main.py`

Modified the `evar_detail` route to:
1. Fetch eVar configuration from API 1.4 using the new `get_evar()` method
2. Merge the API 1.4 configuration into the API 2.0 dimension data
3. Cache both the dimension data and eVar configuration separately

Key changes:
```python
# Fetch both API 2.0 dimension and API 1.4 eVar config
api_v14 = get_api_service_v14()

def fetch_evar_config():
    """Fetch eVar configuration from API 1.4 (has allocation, expiration, merchandising)"""
    return api_v14.get_evar(rsid, display_id)

# ... parallel fetching with caching ...

# Merge API 1.4 eVar configuration into dimension data
if evar_config:
    dimension = dimension.copy() if dimension else {}
    dimension.update({
        'allocation_type': evar_config.get('allocation_type'),
        'expiration_type': evar_config.get('expiration_type'),
        'expiration_custom_days': evar_config.get('expiration_custom_days'),
        'merchandising_syntax': evar_config.get('merchandising_syntax'),
        'binding_events': evar_config.get('binding_events'),
        'enabled': evar_config.get('enabled')
    })
```

### 3. Updated Detail Template to Display Configuration

**File:** `app/templates/detail.html`

Updated the template to:
1. Format allocation_type enum values (e.g., `'merchandising_last'` → "Merchandising (Last)")
2. Format expiration_type values (e.g., `'page_view'` → "Hit")
3. Format merchandising_syntax values (e.g., `'product'` → "Enabled")
4. Display merchandising type (Product Syntax vs Conversion Variable Syntax)

Added new rows to the configuration table:
```html
<tr>
    <th>Allocation</th>
    <td>Merchandising (Last)</td>
</tr>
<tr>
    <th>Expiration</th>
    <td>Hit</td>
</tr>
<tr>
    <th>Enable Merchandising</th>
    <td>Enabled</td>
</tr>
<tr>
    <th>Merchandising</th>
    <td>Product Syntax</td>
</tr>
```

## API 1.4 Data Format

The `ReportSuite.GetEvars` endpoint returns eVar configuration with these fields:

```json
{
  "id": "evar1",
  "name": "Product Location (imp & cart add) [merch v1]",
  "allocation_type": "merchandising_last",
  "expiration_type": "page_view",
  "expiration_custom_days": "1",
  "merchandising_syntax": "product",
  "binding_events": [],
  "enabled": true,
  "type": "text_string",
  "description": "..."
}
```

### Enum Value Mappings

**allocation_type:**
- `most_recent_last` → "Most Recent (Last)"
- `original_value_first` → "Original Value (First)"
- `linear` → "Linear"
- `linear_to_items` → "Linear (to Items)"
- `merchandising_last` → "Merchandising (Last)"
- `merchandising_first` → "Merchandising (First)"

**expiration_type:**
- `page_view` or `hit` or `0` → "Hit"
- `visit` or `1` → "Visit"
- `day` or `2` → "Day"
- `week` or `3` → "Week"
- `month` or `4` → "Month"
- `quarter` or `5` → "Quarter"
- `year` or `6` → "Year"
- `purchase_event` or `7` → "Purchase Event"
- `product_view` or `8` → "Product View"
- `never` or `9` → "Never"

**merchandising_syntax:**
- `product` or `1` → "Enabled" (Product Syntax)
- `conversion_variable_syntax` → "Enabled" (Conversion Variable Syntax)
- `none` or `0` → "Disabled"

## Caching Strategy

The fix implements separate caching for:
1. **API 2.0 Dimension Data:** Cached as `evar_detail_{evar_id}` (e.g., `evar_detail_evar1`)
2. **API 1.4 eVar Config:** Cached as `evar_config_{evar_id}` (e.g., `evar_config_evar1`)

Both are fetched in parallel using `ThreadPoolExecutor` for optimal performance.

## Known Limitations

### eVars Table View

The eVars listing page (`/evars`) still shows empty values for Allocation and Expiration columns because:
1. The table uses API 2.0 dimensions which don't include these fields
2. Fetching all eVar configurations from API 1.4 would require an additional API call
3. For MVP velocity, the table view is acceptable as-is since users can click through to detail pages for full configuration

A comment has been added to the code documenting this limitation:
```python
# NOTE: API 2.0 dimensions don't include allocation/expiration fields, so these columns
# will be empty in the table view. Full configuration (including allocation, expiration,
# and merchandising) is available on the eVar detail pages via API 1.4.
```

## Testing

Verified the fix by:
1. Clearing the cache
2. Loading `/evars/evar1`
3. Confirming all configuration fields display correctly:
   - **Allocation:** Merchandising (Last) ✅
   - **Expiration:** Hit ✅
   - **Enable Merchandising:** Enabled ✅
   - **Merchandising:** Product Syntax ✅

These values now match what is shown in the Adobe Analytics Admin Console.

## Files Modified

1. `app/services/adobe_analytics.py` - Added `get_evar()` method
2. `app/routes/main.py` - Updated `evar_detail` route to fetch and merge API 1.4 config
3. `app/templates/detail.html` - Updated template to display and format eVar configuration fields

## Technical Notes

- The fix leverages the hybrid API approach (API 2.0 + API 1.4) already used for Processing Rules
- Performance impact is minimal due to parallel fetching and caching
- The solution is backward-compatible and doesn't break existing functionality

## Related Documentation

- Adobe Analytics API 1.4 Swagger: `docs/adobe_analytics_api_1.4_swagger.json`
- API Migration Plan: `docs/api-migration.md` (Section 5.5 - Data Model Mapping)

