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

## Detail Page (`/segments/<segment_id>`)

### `app/services/adobe_analytics_v2.py` — `get_segment()`

Fetches a single segment by ID using `GET /segments/{id}` with full expansion (`definition`, `compatibility`, `tags`, `ownerFullName`, `modified`).

### `app/routes/main.py` — `_parse_segment_schema()` helper + `segment_detail()` route

`_parse_segment_schema(schema)` converts the flat `compatibility.schema` list (e.g. `"attribute_variables/evar22"`, `"event_metrics/event21"`, `"container_hits"`) into grouped `{'container', 'variables', 'events'}` for the template.

The route caches each segment detail under `segment_detail_{id}` (24h TTL).

### `app/templates/segment_detail.html`

Two-column layout:
- **Left:** ID, name, description, owner + login, modified date, container scope badge, tags, RSID, referenced variables/events (clickable badge links to eVar/prop/event detail pages), compatibility status and supported products.
- **Right:** Raw definition JSON in a scrollable `<pre>` block.

## Listing page improvements

- `ID` column removed — not useful to end users.
- `Name` column is a clickable link to the detail page. The segment ID is attached to each row as a non-column field (`segment_id`) so the template can build the link without displaying the ID. Same pattern used by Prop/eVar/Event ID columns.
- `column_styles` parameter added to `render_listing()` and `listing.html`, allowing per-column inline CSS. Segments passes `max-width:320px; white-space:normal; word-break:break-word;` on the Name column so absurdly long names wrap rather than stretching the table.

## API quirks discovered

- The `/segments` endpoint defaults to returning only segments **owned by** the authenticated service account — which owns zero segments for a server-to-server integration. Fix: `includeType=all` + `rsids=<rsid>` returns all 3,596 segments associated with the report suite.
- An initial call without `includeType` cached an empty `[]` result (24h TTL). The stale cache had to be manually deleted before the fix took effect.

## Bug fixed: cache page crash (`'keys'` shadowing)

`CacheService.get_info()` returned a dict with key `'keys'`. In Jinja2, `cache_info.keys` resolves via `getattr` first — returning the built-in `dict.keys` method, not the stored value. This made `{% if cache_info.keys %}` truthy (a method is truthy) and `cache_info.keys.items()` then crashed.

Fix: renamed the key to `'cache_keys'` in both `CacheService.get_info()` and `cache.html`.

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | `get_segments()` (with `includeType=all`), `get_segment()` |
| `app/routes/main.py` | `SEGMENTS_COLUMNS` (no ID), `render_listing()` gains `column_styles`, `_parse_segment_schema()` helper, `/segments` route (segment_id attachment, column_styles), `/segments/<segment_id>` detail route |
| `app/templates/listing.html` | `column_styles` support, `Name` → segment detail link |
| `app/templates/segment_detail.html` | New detail template |
| `app/templates/base.html` | Segments nav item |
| `app/services/cache_warmer.py` | `'segments'` in cache keys + fetch map |
| `app/routes/main.py` (overview) | Segments stat |
| `app/templates/overview.html` | Segments card (3-col row) |
| `app/services/cache.py` | Rename `'keys'` → `'cache_keys'` in `get_info()` |
| `app/templates/cache.html` | `cache_info.cache_keys` |

## API Details

- **List endpoint:** `GET /{globalCompanyId}/segments` — params: `rsids`, `includeType=all`, `expansion=ownerFullName,modified,tags`, `limit=1000`, `page`, `sortProperty=name`
- **Detail endpoint:** `GET /{globalCompanyId}/segments/{id}` — params: `expansion=ownerFullName,modified,tags,definition,compatibility`
- **Auth:** OAuth 2.0 (same token as all other 2.0 calls)
- **API version:** 2.0 only — no 1.4 fallback needed or used

## Testing

1. Navigate to `/segments`. Verify the DataTable loads with Name, Owner, Modified, Tags, Description columns (no ID column).
2. Check that a long segment name wraps within its cell rather than stretching the table.
3. Click a segment name — verify the detail page opens with configuration, referenced dimensions, and definition JSON.
4. Verify clickable badge links on the detail page navigate to the correct eVar/prop/event detail pages.
5. Use the DataTables search box to filter by owner or tag name.
6. Click "Export CSV" — verify the download contains all listing columns.
7. Check the Overview page — the Segments card should show the count once the cache is warm.
8. Navigate to `/cache` — verify the per-key table renders without error and shows a `segments` row.
