# 027 — Calculated Metrics Listing & Detail Page (API 2.0)

**Date:** March 26, 2026
**Status:** Completed
**Branch:** `feature/calculated-metrics`

## Problem

The todo listed "Add a Metrics listing page (API 2.0 `/metrics` endpoint)". The `/metrics` endpoint returns all native metrics (page views, visits, custom events, etc.) — many of which already appear in the Events page as `metrics/event*`. Calculated metrics were a better target:

- They live at `/calculatedmetrics` (API 2.0 only)
- They are user-defined, named, and described — documentation-worthy
- They are entirely missing from Codex
- They reference native metrics and segments, giving natural cross-links to the rest of the app

There were 962 calculated metrics in the report suite.

## API Quirk: `includeType=all`

Same issue as segments (autopsy 025): the `/calculatedmetrics` endpoint defaults to returning only calculated metrics *owned by* the service account (zero). `includeType=all` with `rsids=<rsid>` returns all company-level metrics associated with the report suite.

| Params | Count |
|--------|-------|
| `rsids` only | 0 |
| `rsids` + `includeType=all` | 962 |
| `rsids` + `includeType=shared` | 3 |

## Implementation

### Service methods — `adobe_analytics_v2.py`

**`get_calculated_metrics(rsid)`** — paginated fetch (1000/page), returns flat dicts: `id, name, description, type, polarity, precision, owner, modified, tags`.

**`get_calculated_metric(cm_id)`** — single fetch with full expansion (`definition`, `tags`, `ownerFullName`, `modified`). Returns empty dict on error.

### Formula parser — `main.py`

Two helpers for the detail page:

**`_walk_formula(node, metrics, segments)`** — recursive DFS over the formula JSON tree. Collects:
- `func: 'metric'` nodes → native metric (id, description)
- `func: 'segment-ref'` nodes → segment (id, description)

Handles arbitrary nesting depth (operators like `divide`, `add`, `if`, etc. all recurse into their child nodes via generic dict/list traversal).

**`_parse_calc_metric_formula(definition)`** — calls `_walk_formula` and returns sorted `{'metrics': [(id, desc)], 'segments': [(id, desc)]}`.

### Routes

| URL | Description |
|-----|-------------|
| `GET /calculated-metrics` | Listing page |
| `GET /calculated-metrics/export` | CSV export |
| `GET /calculated-metrics/<cm_id>` | Detail page |

The listing attaches `cm_id` to each row (non-column field) so `listing.html` can build detail links — same pattern as segments.

Detail pages cache per-metric under `cm_detail_<id>` (24h TTL).

### `listing.html`

Added `{% elif col == 'Name' and row.cm_id %}` link case alongside existing Prop/eVar/Event/Segment cases.

### Column mapping — `CALC_METRICS_COLUMNS`

`Name, Type, Owner, Modified, Tags, Description` — ID excluded (not useful to end users; shown on detail page instead).

Name column uses `max-width:320px; white-space:normal; word-break:break-word;` via `column_styles` to handle long names.

### Detail page — `calc_metric_detail.html`

Two-column layout:

**Left:**
- Configuration card: ID, name, description, owner (+login), modified, type badge, polarity badge (positive↑ / negative↓), decimal places, tags, RSID
- Formula References card: native metrics as badges (events link to `/events/<id>`), segments as badges linking to `/segments/<id>`

**Right:**
- Raw formula definition JSON in a scrollable `<pre>` block

### Navigation

Added **Calc. Metrics** nav item between Segments and the More dropdown.

### Cache

- `'calculated_metrics'` added to `CONFIG_CACHE_KEYS` and `fetch_map` in `cache_warmer.py`
- Overview route reads `_calc_metrics_raw = cache.get(rsid, 'calculated_metrics')`

### Overview page

New third row with a Calculated Metrics count card (links to `/calculated-metrics`). Kept as a half-width card (`col-sm-6`) with room for a future companion card.

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_analytics_v2.py` | `get_calculated_metric()`, `get_calculated_metrics()` |
| `app/routes/main.py` | `from typing import Any`; `_walk_formula()`, `_parse_calc_metric_formula()` helpers; `CALC_METRICS_COLUMNS`; three routes; overview stats |
| `app/templates/listing.html` | `cm_id` Name link case |
| `app/templates/calc_metric_detail.html` | New detail template |
| `app/templates/base.html` | Calc. Metrics nav item |
| `app/services/cache_warmer.py` | `'calculated_metrics'` in keys + fetch map |
| `app/templates/overview.html` | Third stats row with Calculated Metrics card |
