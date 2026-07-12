# Meridian — Release Summary

> A data dictionary and configuration intelligence tool for Adobe Analytics report suites.
> Converted from R/Shiny to Python/Flask and progressively extended from v1 to v2.

---

## Version 1 — Foundation

Version 1 established the core data dictionary: a read-only, web-based reference for understanding how an Adobe Analytics report suite is configured.

### What it delivered

| Feature | Description |
|---------|-------------|
| **eVars (Conversion Variables)** | Browse all eVars with allocation model, expiration, and description |
| **Props (Traffic Variables)** | View all props with pathing and list-prop settings |
| **Success Events** | List all custom events with type, serialisation setting, and description |
| **List Variables (ListVars)** | View ListVar configurations and delimiters |
| **Detail pages** | Drill into any individual variable for full configuration details |
| **Dimension Notes** | Annotate any variable with plain-English descriptions and technical context, stored locally |
| **CSV Export** | Export any configuration table for documentation or audits |

### Technology

- Python 3.13, Flask, Jinja2 templates, Bootstrap 5
- DataTables for sortable, filterable, exportable tables
- Adobe Analytics API 1.4 (WSSE authentication)

---

## Version 2 — Extended Intelligence

Version 2 significantly expanded the scope of Meridian — adding new data sources, new pages, deeper cross-referencing, and improved reliability. All work below has been completed and merged.

### New Pages

| Feature | What it does |
|---------|-------------|
| **Report Suite Overview** | Landing page showing a snapshot of the report suite: variable counts, utilisation stats, and cache status at a glance |
| **Segments** | Browse all segments defined in the report suite; detail pages show owner, tags, and a human-readable breakdown of referenced dimensions and events |
| **Calculated Metrics** | List all calculated metrics with formula cross-references; detail pages show referenced metrics and segments, plus a **30-day trend chart** |
| **Processing Rules** | Display all processing rules grouped by rule set, with conditions and actions formatted for readability |
| **Marketing Channels** | Browse channel definitions, order, and settings |
| **Channel Rules** | View the marketing channel classification rules that determine how each visit is attributed |
| **Report Suites** | List all report suites in the authenticated Adobe Analytics company with key configuration stats |
| **API Debug** | Interactive browser-based explorer for all Adobe Analytics API 1.4 and 2.0 endpoints — browse, inspect parameters, and send read-only requests proxied securely through the server |
| **Cache Management** | View cache status for all data sources, see age and creation time, and force-refresh individual caches on demand |

### Cross-Referencing & Data Lineage

These features appear on the **detail pages** for Props, eVars, Events, and ListVars — answering the question *"where does this variable get used?"*

| Feature | What it shows |
|---------|--------------|
| **Related Processing Rules** | Which processing rules read from or write to this variable |
| **Components panel** | Which Segments and Calculated Metrics reference this variable (including transitive references via nested segments inside calculated metrics) |
| **Data Feed column name** | The raw data feed column name (e.g. `post_evar5`, `post_prop3`) for use in data engineering and feed analysis |

### Reliability & Performance

| Improvement | Details |
|-------------|---------|
| **Background pre-caching** | All configuration data is pre-warmed at startup and refreshed every 24 hours — users never wait for a cold cache load |
| **API 1.4 endpoint fallback** | Automatically retries on alternative Adobe API domains (`api2`, `api3`, `api4.omniture.com`) if the primary endpoint is unresponsive — important as Adobe's 1.4 infrastructure enters end-of-life |
| **Graceful API error handling** | If the API is unreachable, the app still loads with a user-friendly error rather than a crash |

### Quality & UX Improvements

- Processing Rules conditions and actions reformatted with proper indentation and structure — significantly more readable for complex multi-condition rules
- Monospace styling standardised across processing rule and dimension detail pages
- Marketing Channels and Channel Rules consolidated into a single navigation dropdown
- Active navigation state properly reflected in all dropdown items
- DataTables column widths enforced on wide tables (e.g. Processing Rules) to prevent long-text columns from dominating the layout

### Architecture & Deployment

| Improvement | Details |
|-------------|---------|
| **Multisite routing** | Single Meridian deployment serves multiple clients; all routes prefixed `/<client>/`; credentials stored as per-client JSON files in `MERIDIAN_SECRETS_DIR` |
| **Brochure site** | Product landing page served at `/` from within the Flask app; client dashboards continue at `/<client>/` |

---

## What's Next (Planned)

| Feature | Description |
|---------|-------------|
| **Per-user OAuth login** | Replace the shared server credential with individual Adobe IMS login, enabling per-user access control. Config scaffolding is in place; full implementation planned. |

---

## Architecture at a Glance

```
Meridian
├── Flask web application (Python 3.13, uv)
├── Multi-client routing (/<client>/ URL prefix, MERIDIAN_SECRETS_DIR)
├── Adobe Analytics API 1.4 client (WSSE — processing rules, marketing channels)
├── Adobe Analytics API 2.0 client (OAuth2 — eVars, Props, Events, Segments, Calculated Metrics)
├── Adobe Reactor API client (Launch rules, Tags integration)
├── JSON file-based cache with APScheduler background refresh
├── Jinja2 + Bootstrap 5 templates with DataTables
└── Docker-ready (docker-compose.yml included)
```

**Live demo:** [https://meridian.aerobee.com.au](https://meridian.aerobee.com.au)

---

*Last updated: April 2026*
