# 025 — Segments Listing Page (API 2.0)

**Date:** March 26, 2026
**Status:** Completed
**Branch:** `feature/segments-listing`

## Problem

Codex surfaces eVars, props, events, processing rules, and marketing channels, but had no page for **segments** — one of the most commonly used artefacts in Adobe Analytics. Segments are used by every analyst to scope reports, and being able to see all saved segments (name, owner, tags, last modified) in one place fills an obvious gap in the configuration documentation.

The API 2.0 `/segments` endpoint has been available since the 2.0 migration but was never wired up.

---

## Approach

Followed the same listing-page pattern already established for evars, props, events, etc.:

1. Add a `get_segments()` method to `AdobeAnalyticsV2Service`.
2. Add `/segments` and `/segments/export` routes to `main.py`.
3. Add a nav link in `base.html`.
4. Add segments to the cache warmer and the overview stats row.

No new template was needed — `listing.html` handles it generically.

---

## Implementation

### `app/services/adobe_analytics_v2.py` — `get_segments()`

Fetches all segments tied to the configured RSID using the `/segments` endpoint with pagination (`limit=1000`, iterating pages until `totalElements` is reached).

Requested expansion fields: `ownerFullName`, `modified`, `tags`.

Each segment is normalised to a flat dict:

| Key | Source |
|-----|--------|
| `id` | `seg.id` |
| `name` | `seg.name` |
| `description` | `seg.description` |
| `owner` | `seg.owner.name` or `seg.owner.login` |
| `modified` | `seg.modified` (date only — first 10 chars) |
| `tags` | comma-joined tag names from `seg.tags[]` |

### `app/routes/main.py`

- Added `SEGMENTS_COLUMNS` column mapping dict.
- Added `segments()` route (`GET /segments`) — caches under key `segments` with `CONFIG_TTL_HOURS`.
- Added `segments_export()` route (`GET /segments/export`) — same data as CSV.

### `app/templates/base.html`

Added a **Segments** nav item between Channel Rules and the More dropdown.

### `app/services/cache_warmer.py`

- Added `'segments'` to `CONFIG_CACHE_KEYS`.
- Added `'segments': lambda: api_v2.get_segments(rsid)` to the `fetch_map` in `warm_cache_key()`.

### `app/routes/main.py` — overview route

Reads `_segments_raw = cache.get(rsid, 'segments')` and adds a `stats['segments']` entry so the overview page can show the count without triggering an API call.

### `app/templates/overview.html`

Changed the second stats row from 2 × `col-sm-6` to 3 × `col-sm-4` and added a Segments card alongside Processing Rules and Marketing Channels.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | New `get_segments()` method |
| `app/routes/main.py` | `SEGMENTS_COLUMNS`, `/segments`, `/segments/export` routes; segments stat in overview route |
| `app/templates/base.html` | Segments nav item |
| `app/services/cache_warmer.py` | `'segments'` added to cache keys and fetch map |
| `app/templates/overview.html` | Segments card in second stats row |

---

## API Details

- **Endpoint:** `GET /{globalCompanyId}/segments`
- **Key params:** `rsids`, `expansion=ownerFullName,modified,tags`, `limit`, `page`, `sortProperty=name`
- **Auth:** OAuth 2.0 (same token as all other 2.0 calls)
- **API version:** 2.0 only — no 1.4 fallback needed or used

---

## Testing

1. Navigate to `/segments`. Verify the DataTable loads with Name, ID, Owner, Modified, Tags, Description columns.
2. Use the DataTables search box to filter by owner or tag name.
3. Click "Export CSV" and verify the download contains all columns.
4. Check the Overview page — the Segments card should show the count once the cache is warm.
5. On a cold cache, verify `/segments` triggers an API call and caches the result.
6. Trigger `/cache/refresh/segments` and confirm the cache re-warms correctly.
