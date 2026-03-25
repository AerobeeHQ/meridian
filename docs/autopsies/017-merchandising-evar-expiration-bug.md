# 017 — Merchandising eVar Expiration Display Bug

## Problem

Merchandising eVars with "Purchase Event" expiration (e.g. eVar39 in Coles Global Prod) incorrectly displayed **"1 Days"** instead of **"Purchase Event"** on the detail page.

## Root Cause

The detail page relied on the API 1.4 `expiration_type` field, which can return an **integer** (e.g. `7`) rather than a **string** (`"7"`). In Python/Jinja2, `7 == '7'` evaluates to `False`, so the template's string comparison chain failed to match any known expiration type. It then fell through to the `custom_days` branch where `expiration_custom_days: 1` (a default value) produced "1 Days".

## Fix — Parse Expiration from API 2.0 Description

Rather than fixing the API 1.4 type coercion (API 1.4 is deprecated August 2026), we now extract expiration and allocation data from the **API 2.0 `description` field**, which embeds this metadata as structured text:

```
Expiration: Purchase.
Allocation: Merchandising (Last)
```

### Changes

#### 1. New parser: `AdobeAnalyticsV2.parse_description_metadata()` (`app/services/adobe_analytics_v2.py`)

Static method that extracts `expiration_type`, `expiration_custom_days`, and `allocation_type` from the description text. Maps human-readable labels ("Purchase", "Hit", "Never", etc.) to canonical keys the template expects (`purchase_event`, `hit`, `never`, etc.). Handles custom-day formats like "30 Days".

#### 2. Updated `_transform_dimension_to_evar()` (`app/services/adobe_analytics_v2.py`)

Now calls the parser to populate `expiration_type`, `expiration_custom_days`, and `allocation_type` from the description — instead of relying on non-existent structured API 2.0 fields.

#### 3. Updated `evar_detail` route (`app/routes/main.py`)

- Parses expiration/allocation from API 2.0 description **first** (primary source).
- Falls back to API 1.4 data only for fields the description doesn't contain (merchandising_syntax, binding_events, enabled), or as a backfill if the description didn't include expiration metadata.

#### 4. Template hardening (`app/templates/detail.html`)

- Added `|string` filter on `expiration_type` for defence-in-depth.
- Added explicit `'custom'` type handling.
- Added `'None'` guard for the raw-value fallback.

## Files Changed

- `app/services/adobe_analytics_v2.py` — new `parse_description_metadata()` + updated `_transform_dimension_to_evar()`
- `app/routes/main.py` — API 2.0-first expiration/allocation with API 1.4 fallback
- `app/templates/detail.html` — template hardening

## Why This Approach

- **API 1.4 deprecation:** Adobe is retiring API 1.4 in August 2026. Parsing the description reduces our dependency on it.
- **Data already there:** The API 2.0 description field consistently includes `Expiration:` and `Allocation:` metadata — no additional API calls needed.
- **Graceful degradation:** API 1.4 remains as a fallback for merchandising-specific fields and for descriptions that don't contain metadata.

## Testing

Manual: load a merchandising eVar detail page (e.g. eVar39, eVar10) and verify the Expiration field shows "Purchase Event" instead of "1 Days". Also verify non-merchandising eVars (e.g. eVar109 → "Never", eVar1 → "Hit").
