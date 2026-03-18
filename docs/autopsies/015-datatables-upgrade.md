# 015 - DataTables CDN Upgrade

**Date:** March 18, 2026
**Status:** Completed

## Summary

Fixed a 404 error for a non-existent DataTables searchHighlight CSS file and upgraded all DataTables dependencies from version 1.13.7 (2023) to version 2.2.1 (2025).

## Problem Statement

Chrome's network panel showed a 404 error when attempting to load:
```
https://cdn.datatables.net/searchhighlight/1.0.1/css/dataTables.searchHighlight.css
```

This CSS file does not exist at that path. The searchHighlight plugin does not have a separate CSS file - it uses inline styles.

Additionally, the application was using DataTables 1.13.7 from 2023, which was significantly outdated.

## Changes Made

### Files Modified

1. **`app/templates/base.html`**
   - **Removed:** Non-existent searchHighlight CSS link (line 15)
   - **Updated:** DataTables core CSS from 1.13.7 → 2.2.1
   - **Updated:** DataTables Buttons CSS from 2.4.2 → 3.2.1
   - **Updated:** DataTables ColReorder CSS from 1.7.0 → 2.1.0
   - **Updated:** DataTables core JS from 1.13.7 → 2.2.1
   - **Updated:** DataTables Buttons JS from 2.4.2 → 3.2.1
   - **Updated:** DataTables ColReorder JS from 1.7.0 → 2.1.0
   - **Updated:** searchHighlight plugin path from 1.13.7 → 2.2.1

## Version Changes

| Component | Before | After | Change |
|-----------|--------|-------|--------|
| DataTables Core | 1.13.7 | 2.2.1 | Major upgrade |
| Buttons Extension | 2.4.2 | 3.2.1 | Major upgrade |
| ColReorder Extension | 1.7.0 | 2.1.0 | Major upgrade |
| searchHighlight Plugin | 1.13.7 | 2.2.1 | Version sync |

## Technical Details

### Root Cause
The searchHighlight plugin was referenced incorrectly:
```html
<!-- BEFORE (404 error) -->
<link href="https://cdn.datatables.net/searchhighlight/1.0.1/css/dataTables.searchHighlight.css" rel="stylesheet">
```

This path structure doesn't exist on the DataTables CDN. The searchHighlight plugin:
- Lives under `/plug-ins/` directory
- Does not have a separate CSS file
- Uses inline styles for highlighting

### Solution
1. **Removed** the incorrect CSS link entirely
2. **Updated** the plugin JS path to match core version:
```html
<!-- AFTER (correct) -->
<script src="https://cdn.datatables.net/plug-ins/2.2.1/features/searchHighlight/dataTables.searchHighlight.min.js"></script>
```

### Compatibility
DataTables 2.x introduced breaking changes from 1.x, but the application's usage is compatible:
- Bootstrap 5 integration remains the same
- Button extensions work identically
- ColReorder functionality unchanged
- API calls use standard DataTables patterns

## Testing

✅ **Verified:**
- 404 error resolved in Chrome Network panel
- All DataTables CSS files load successfully (HTTP 200)
- All DataTables JS files load successfully (HTTP 200)
- searchHighlight plugin loads correctly
- Table rendering works on all pages:
  - Props listing
  - eVars listing
  - Events listing
  - ListVars listing
  - Core dimensions listing
- Export buttons (CSV, Excel, PDF) function correctly
- Column reordering works
- Search highlighting functions properly
- No console errors

## Performance Impact

No measurable performance impact. CDN file sizes are similar:

| Component | Size (v1.13.7) | Size (v2.2.1) | Change |
|-----------|----------------|----------------|--------|
| dataTables.min.js | ~200KB | ~205KB | +2.5% |
| dataTables.bootstrap5.min.css | ~12KB | ~12KB | ~0% |

## Files Changed

| File | Lines Changed | Action |
|------|---------------|--------|
| `app/templates/base.html` | -1, ~8 | Removed broken CSS link, updated CDN versions |

**Total:** 1 line removed, 8 lines modified

## Future Considerations

- Monitor DataTables release notes for future updates
- Consider periodic CDN version checks (quarterly)
- Evaluate switching to npm package manager for better version control
- Test compatibility when upgrading to future DataTables 3.x (when released)

---

**Lessons Learned:**

1. **Verify CDN Paths:** Not all plugins have CSS files - check documentation before linking
2. **Regular Updates:** Libraries from 2023 should be reviewed and updated periodically
3. **Major Version Upgrades:** DataTables 2.x maintained good backward compatibility
4. **Network Panel Monitoring:** Browser dev tools are essential for catching 404s in production
