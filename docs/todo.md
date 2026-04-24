# TODOs and Bugs

This document is a list of smaller todo items and bugs found while using the Codex app.

---

## Active TODOs

- [ ] Consolidate this **todo.md** file into the version-3-roadmap.md file — migrate remaining active items once v3 roadmap is finalised.
- [ ] Add unit tests for critical service layer functions (`adobe_analytics_v2.py`, `adobe_auth.py`, `cache.py`).
- [ ] Consider adding integration tests for key routes with mocked API responses.
- [ ] Add a `GET /health` endpoint for Docker `HEALTHCHECK` and container orchestration readiness probes (see v3-013).
- [x] `notes.py` hard-codes the notes directory path relative to `__file__` — should use `CODEX_SECRETS_DIR` or an env-configured path for portability across deployments. Also fixed per-client cache dirs in `app/__init__.py`. **[autopsy 059](autopsies/059-persistent-data-dirs.md)**
- [x] Persist the search term between prop,eVar, events, and listVar listing pages. Extended to Segments and Calculated Metrics pages too. Escape key clears the search. **[autopsy 058](autopsies/058-persist-listing-search.md)**
- [ ] Add Tags as a column to the Props/eVars/Events/ListVars listing pages, so that the user can search for them.
- [ ] Add a Report Suite selector to the NavBar? Needs research to get the right ux.
- [ ] The Adobe Launch section of the Props/eVars/Events detail pages should display ALL properties that set/modify that data dimension. Only the currently published production library should be searched.
- [ ] Update the dashboard page to call out any anomalies in data collection. Investigate whether API 2.0 offers this. Anomalies would be data dimensions suddenly reporting zero, suddenly reporting a new top 10 values, suddenly reporting a much higher volume. (But what timeframe, and some data is very spiky, so how to define "anomaly"??)
- [ ] Can this project be distributed as an exectutable installable app? exe or mac .app? Would it be electron (blech) or native (eeek)?

---

## Active Bugs

- [x] **Typo in navbar tooltip:** `base.html` line ~321 has `title="Traffice Variables"` — fixed to `"Traffic Variables"`. **[autopsy 058](autopsies/058-persist-listing-search.md)**
- [ ] **No custom 404/500 error pages:** Only `_api_error.html` (for Adobe API errors) exists. Flask's default HTML error pages are returned for missing routes and unhandled server errors — these leak the Flask version and look broken.
- [ ] **CSRF exposure on write routes:** `POST /api/notes`, `DELETE /api/notes`, `POST /api/tags`, and `DELETE /api/tags` have no CSRF token validation. Requests can be forged from any origin that can reach the server (see v3-012).
- [ ] If there is a problem with the Adobe API2 credentials then the props/eVars/events/listVars listing pages will fail to load and show an error message about Adobe Analytics API 1.4 Unavailable, which is misleading. The app should detect which API is having issues and show a more accurate error message (see autopsy 046 for API debug page improvements, which would also help surface these issues).
- [ ] Tags on Prop/eVar/Event pages appear to be broken. It displays a message: "Failed to save", and trying to add a new one doesn't work, and doesn't show an error. (It doesn't need error handling, it just needs to work)

---

## Code Quality / Technical Debt

- [ ] **Template consolidation:** `detail.html`, `event_detail.html`, and `listvar_detail.html` are ~75% structurally identical. Consolidate into a shared base template with Jinja2 blocks (deferred from autopsy 035).
- [ ] **Route file size:** `main.py` is ~2,700 lines. Consider splitting into multiple blueprints (deferred from autopsy 035).
- [ ] **Inline CSS extraction:** `base.html` contains ~160 lines of inline CSS. Consider extracting to `static/css/style.css`.
- [ ] **Cache file locking:** `CacheService` does not implement file locking, which could cause race conditions under concurrent writes. Not a practical issue at current scale, but worth addressing if usage increases.

---

## Descoped

- [ ] ~~**Item 5. ListVar 30-day trend chart**~~ — Same as props, but `get_dimension_trend()` is already available. ListVar detail pages could add the same chart pattern but this was descoped due to low priority.

---

## Suggested Improvements (for V3 consideration)

- [ ] **User OAuth login (Roadmap v3-001)** — Replace server-to-server credential with per-user Adobe IMS login. Config scaffolding in place (`AUTH_MODE`, `OAUTH_REDIRECT_URI`, `SESSION_SECRET`); full implementation planned for v3.
- [ ] **Adobe Spectrum theme (Roadmap v3-005)** — Add as a theme option in Settings page. Requires integration with `@adobe/spectrum-web-components`.
- [ ] **Multi-client report suite selection (Roadmap v3-003)** — Allow users to select a specific report suite in Settings, rather than using the config file default.
- [ ] **Adobe Launch property mapping (Roadmap v3-004)** — In Settings, allow users to map a specific Launch property to the selected report suite.
- [ ] **Self-hosted assets (Roadmap v3-006)** — Remove dependency on third-party CDNs for CSS, icons, and fonts.
- [ ] **Configuration change detection (Roadmap v3-009)** — Compare consecutive 24-hour cache snapshots and surface changes (renamed eVars, changed allocation/expiration) on the Overview page.
- [ ] **Implementation health scorecard (Roadmap v3-010)** — Flag unused variables, variables missing names/notes, and duplicate display names on the Overview page.
- [ ] **Export enhancements (Roadmap v3-011)** — Single-click multi-sheet Excel workbook export; print-friendly detail page layout.
- [ ] **HTTP security hardening (Roadmap v3-012)** — CSRF protection on write routes; standard HTTP security headers (CSP, X-Frame-Options, etc.).
- [ ] **Health check endpoint (Roadmap v3-013)** — `GET /health` JSON route for Docker `HEALTHCHECK` and uptime monitoring.

---

## Dones

Completed items from Version 2 development. Use git history/blame to track completion dates.

### v2 TODOs Completed

*Last updated: 2026-04-19*

- [x] In the Components panel on prop/evar/event/listvar detail pages, use the pill style already being used on the Segment/Metric details page instead of the plain hyperlink. **[autopsy 028](autopsies/028-components-panel.md)**
- [x] Hyperlink the segmentId and metricId shown on their respective detail pages to Adobe Analytics. **[autopsy 042](autopsies/042-segment-metric-experience-cloud-links.md)**
- [x] Hyperlink the Adobe Launch rule into Adobe Tags website. **[autopsy 043](autopsies/043-launch-adobe-tags-deeplinks.md)**
- [x] Add a "Known Issues" section to the README. **Done in README.md**
- [x] Add a "Version History" section to the README. **Done in README.md**
- [x] Move the processing/channel/launch panels on detail pages from left to right column. **[autopsy 044](autopsies/044-detail-page-panel-layout.md)**
- [x] Allow users to manage (CRUD) tags. **[autopsy 047](autopsies/047-tags-crud.md)**
- [x] Improve listing pages (lighter shading, sticky headers, toolbar consolidation). **[autopsy 044](autopsies/044-listing-page-improvements.md)**
- [x] Create a Codex brochure site. **[autopsy 051](autopsies/051-brochure-site.md)**
- [x] Reorganize site structure for multisite routing. **[autopsy 052](autopsies/052-multisite-routing.md)**
- [x] Add the allocation and expiration data to the data dimensions listing page. **[autopsy 018](autopsies/018-evar-listing-expiration-allocation.md)**
- [x] Change the data dimensions listing page template name (`table.html` → `listing.html`). **[autopsy 019](autopsies/019-rename-table-template.md)**
- [x] Add a Segments listing page. **[autopsy 025](autopsies/025-segments-listing.md)**
- [x] Add a Calculated Metrics listing and detail page. **[autopsy 027](autopsies/027-calculated-metrics.md)**
- [x] Create a debug page for API 1.4 and 2.0 endpoints. **[autopsy 034](autopsies/034-api-debug-page.md)**
- [x] Update the "Report Suites" page. **[autopsy 031](autopsies/031-report-suites-page.md)**
- [x] Cleanup monospace text on Processing Rules pages. **[autopsy 030](autopsies/030-processing-rules-monospace.md)**
- [x] Consolidate Marketing Channels and Channel Rules into one dropdown. **[autopsy 026](autopsies/026-channels-nav-dropdown.md)**
- [x] Display the Data Feed column name in dimension details. **[autopsy 032](autopsies/032-data-feed-column.md)**
- [x] Reformat Processing Rules pseudo-code for readability. **[autopsy 033](autopsies/033-processing-rules-formatting.md)**
- [x] Update the README with latest changes. **[autopsy 055](autopsies/055-review-documentation.md)**
- [x] Add a Components panel to detail pages. **[autopsy 028](autopsies/028-components-panel.md)**
- [x] Pre-Launch Architecture Review. **[autopsy 035](autopsies/035-pre-launch-architecture-review.md)**
- [x] Move Swagger files to `assets/swagger/`. **Done in autopsy 035**
- [x] Add Reactor Debug page. **[autopsy 039](autopsies/039-reactor-debug-page.md)**
- [x] Themes & Settings page. **[autopsy 056](autopsies/056-themes-settings.md)**

### v2 Bugs Fixed

*Last updated: 2026-04-19*

- [x] Data Feed Column for classified values shows incorrect column name. **Fixed — classifications now show parent dimension**
- [x] API debug page blocks all POST requests, but some are read-only by design. **[autopsy 046](autopsies/046-api-debug-readonly-post.md)**
- [x] Trendline chart shows incorrect data for variables with no recent activity. **[autopsy 048](autopsies/048-trendline-data-accuracy.md)**
- [x] Merchandising eVar expiration data shown incorrectly. **[autopsies 016 & 017](autopsies/016-evar-allocation-expiration-fix.md)**
- [x] API 1.4 endpoint unreliability — added fallback to alternative domains. **Done in `adobe_analytics.py`**
- [x] Prop and eVar detail pages don't display calculated metrics (transitive reference). **[autopsy 029](autopsies/029-components-calc-metrics-transitive.md)**
- [x] Processing Rules section shown for classifications (not applicable). **[autopsy 041](autopsies/041-hide-rule-panels-for-classifications.md)**

### Quick Wins Completed

- [x] **Item 1. Prop and eVar 30-day trend charts** — Already implemented via `get_dimension_trend()`. **[autopsy 048](autopsies/048-trendline-data-accuracy.md)**
- [x] **Item 2. Data Feed column name on dimension detail pages** — **[autopsy 032](autopsies/032-data-feed-column.md)**
- [x] **Item 3. Processing Rules condition/action formatting** — **[autopsy 033](autopsies/033-processing-rules-formatting.md)**
- [x] **Item 4. Marketing Channel Rules cross-linking** — **Done in v2-002**
- [x] **Item 6. Segment detail: human-readable container breakdown** — **[autopsy 038](autopsies/038-segment-definition-breakdown.md)**
- [x] **Item 7. Adobe Launch integration** — **[autopsy 036](autopsies/036-adobe-launch-integration.md)**
