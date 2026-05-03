# Version 3 Roadmap

This document summarises the planned features for Codex v3. Each item will have a detailed implementation plan in `docs/plans/` once scoped.

---

## Feature Overview

| # | Feature                                                                      | Complexity  | Status     | Plan                                                  |
|---|------------------------------------------------------------------------------|-------------|------------|-------------------------------------------------------|
| 1 | [User OAuth Login](#1-user-oauth-login)                                      | High        | Scaffolded | [v2-004](plans/v2-004-user-oauth-login.md)            |
| 2 | [API 1.4 Deprecation Strategy](#2-api-14-deprecation-strategy)               | High        | Planned    | [v3-002](plans/v3-002-api-14-deprecation-strategy.md) |
| 3 | [Report Suite Selection in Settings](#3-report-suite-selection-in-settings)  | Medium      | Planned    | —                                                     |
| 4 | [Adobe Launch Property Mapping](#4-adobe-launch-property-mapping)            | Low         | Planned    | —                                                     |
| 5 | [Adobe Spectrum Theme](#5-adobe-spectrum-theme)                              | Medium      | Scaffolded | —                                                     |
| 6 | [Self-Hosted Assets](#6-self-hosted-assets)                                  | Low         | Planned    | —                                                     |
| 7 | [Unit & Integration Tests](#7-unit--integration-tests)                       | Medium      | Planned    | —                                                     |
| 8 | [Documentation Improvements](#8-documentation-improvements)                  | Low         | Ongoing    | —                                                     |
| 9 | [Configuration Change Detection](#9-configuration-change-detection)          | Medium      | Planned    | —                                                     |
| 10| [Implementation Health Scorecard](#10-implementation-health-scorecard)       | Medium      | Planned    | —                                                     |
| 11| [Export Enhancements](#11-export-enhancements)                               | Low         | Planned    | —                                                     |
| 12| [HTTP Security Hardening](#12-http-security-hardening)                       | Medium      | Planned    | —                                                     |
| 13| [Health Check Endpoint](#13-health-check-endpoint)                           | Low         | Planned    | —                                                     |

---

## Suggested Implementation Order

Start with architectural improvements before user-facing features:

1. **API 1.4 Deprecation Strategy** (v3-002) — Adobe is retiring API 1.4 in August 2026. Addressing this is the highest-risk item; delay could result in broken functionality.
2. **Unit & Integration Tests** (v3-007) — Establish a testing foundation before adding new features.
3. **Report Suite Selection in Settings** (v3-003) — Low-risk UX improvement that sets up the pattern for other Settings page features.
4. **Adobe Launch Property Mapping** (v3-004) — Depends on v3-003; small incremental change.
5. **Self-Hosted Assets** (v3-006) — Low-effort, removes external dependency.
6. **User OAuth Login** (v3-001) — Largest architectural change. Scaffolding is in place; full implementation.
7. **Adobe Spectrum Theme** (v3-005) — Nice-to-have polish once core features are stable.
8. **Documentation Improvements** (v3-008) — Ongoing throughout v3 development.
9. **Configuration Change Detection** (v3-009) — Low-effort, high-value safety net for detecting accidental configuration changes.
10. **Implementation Health Scorecard** (v3-010) — Builds on existing Overview page data; no new API calls required.
11. **Export Enhancements** (v3-011) — Multi-sheet Excel workbook from existing CSV data; printable detail page.
12. **HTTP Security Hardening** (v3-012) — Address CSRF exposure on write routes and missing security response headers.
13. **Health Check Endpoint** (v3-013) — Trivial route addition; required for Docker/Kubernetes deployments.

---

## Feature Details

### 1. User OAuth Login

**Goal:** Add user login via Adobe IMS OAuth Authorization Code flow as an opt-in authentication mode, using a hybrid token strategy.

**Why:** Enables per-user access control (users only see the Analytics report suites they personally have access to) and puts the app behind a login wall without requiring a separate credential store. Removes the need to share a service account for Analytics data access.

**Constraint (discovered 2026-04-22):** Adobe's **Reactor (Tags/Launch) API does not support User OAuth** — it requires Server-to-Server credentials. A full replacement of S2S is therefore impossible while Launch integration exists. The revised architecture uses a **hybrid model**: user tokens for Analytics API calls, S2S token for Reactor API calls.

**How:** Implement OAuth Authorization Code flow (`/auth/login`, `/auth/callback`, `/auth/logout` routes already stubbed in `app/routes/auth.py`). Add a `UserAuth` class alongside the existing `OAuth2Auth` in `adobe_auth.py`. Wire per-request token selection: Analytics service receives the user's session token; Launch service continues to use the S2S token from config. Add user name + logout link to the nav. Document the Launch service-account limitation in the Settings page. Keep `AUTH_MODE: "server"` as the default; user auth is opt-in.

**Config Scaffolding:** `AUTH_MODE`, `OAUTH_REDIRECT_URI`, `SESSION_SECRET` already in `config.dist.json`.

**Dependency:** v3-012 (HTTP Security Hardening / CSRF) should be in place before or alongside this feature.

**Complexity: High** — touches auth, sessions, API calls, and deployment configuration. Requires Adobe I/O Console setup before coding begins. See [plan v2-004](plans/v2-004-user-oauth-login.md) for full architecture, security analysis, and code outline.

---

### 2. API 1.4 Deprecation Strategy

**Goal:** Develop a plan for dealing with the shutdown of Adobe Analytics API v1.4 (scheduled August 2026).

**Why:** API 1.4 is currently used for:
- Processing Rules (`ReportSuite.ViewProcessingRules`)
- Marketing Channels (`ReportSuite.GetMarketingChannels`)
- Marketing Channel Rules (`ReportSuite.GetMarketingChannelRules`)
- ListVars configuration (`ReportSuite.GetListVariables`)
- eVar detailed config (`ReportSuite.GetEvars` — allocation, expiration, merchandising)

These endpoints have no API 2.0 equivalents. Without a mitigation strategy, these features will stop working.

**Options to explore:**
1. **Manual data upload** — Users export configuration from Adobe Analytics UI and upload to Codex. Note, that the UI doesn't offer any direct export functionality, so it might require users to copy-paste from the UI or take screenshots. YUCK!
2. **AI agent extraction** — An AI agent (or Playwright script) logs into Adobe Analytics on the user's behalf and extracts configuration data from the UI.
3. **Adobe Admin Console API** — Some configuration may be accessible via Adobe Admin APIs (needs investigation).
4. **Feature deprecation** — Accept that some features will no longer be available post-August 2026.

**Complexity: High** — Requires research spike, possibly new integrations or manual workflows.

---

### 3. Report Suite Selection in Settings

**Goal:** Allow users to select a specific report suite in the Settings page, rather than relying on the config file default.

**Why:** Multi-client deployments currently require separate config files per report suite. A Settings-based selection would allow a single config to access multiple report suites (subject to API permissions).

**How:**
1. Fetch available report suites from `get_report_suites()` API (already implemented).
2. Add a dropdown to the Settings page.
3. Store selection in localStorage (client-side) or server-side session.
4. Modify route context to use the selected RSID instead of config default.

**Complexity: Medium** — Requires changes to how routes resolve the RSID; could affect caching strategy.

---

### 4. Adobe Launch Property Mapping

**Goal:** In Settings, allow users to map a specific Launch property to the selected report suite.

**Why:** Launch properties and Analytics report suites don't have a 1:1 relationship. Users may want to view different Launch properties for different report suites within the same Codex client.

**How:** Add a Launch property dropdown to Settings (fetches properties from Reactor API). Store mapping in localStorage or session. Use mapped property when rendering Launch rules on detail pages.

**Dependencies:** Requires v3-003 (Report Suite Selection) to be implemented first.

**Complexity: Low** — Builds on existing Launch integration; mainly UI work.

---

### 5. Adobe Spectrum Theme

**Goal:** Offer Adobe Spectrum as a theme option in the Settings page.

**Why:** Adobe Spectrum is Adobe's design system. Offering it as a theme option would align Codex's look and feel with Adobe's own tools, which may be preferred by users already familiar with Adobe products.

**How:** Integrate `@adobe/spectrum-web-components` library. Map Spectrum design tokens to Bootstrap CSS custom properties. Add a fourth theme option ("Spectrum") to the Settings page theme selector.

**Scaffolding:** The Settings page already has a "Coming Soon" placeholder for Spectrum.

**Complexity: Medium** — Spectrum uses custom elements and its own token system; mapping to Bootstrap is non-trivial.

---

### 6. Self-Hosted Assets

**Goal:** Remove dependency on third-party CDNs for CSS, icons, fonts, and JavaScript libraries.

**Why:** External CDN dependencies can:
- Break if the CDN is unavailable
- Raise privacy/compliance concerns for some deployments
- Slow down page loads if CDN performance is poor

**How:**
1. Download Bootstrap CSS/JS, Chart.js, DataTables, and any icon fonts currently loaded from CDNs.
2. Place in `app/static/vendor/`.
3. Update templates to reference local paths.
4. Update Dockerfile to include these assets.

**Complexity: Low** — Straightforward file download and path updates.

---

### 7. Unit & Integration Tests

**Goal:** Establish a testing foundation with unit tests for the service layer and integration tests for key routes.

**Why:** Currently reliant on manual testing. As the codebase matures, automated tests will catch regressions faster and enable safer refactoring.

**Approach:**
- **Unit tests:** Use `pytest`. Test `CacheService`, `OAuth2Auth`, `AdobeAnalyticsV2Service` methods with mocked HTTP responses.
- **Integration tests:** Use Flask's test client to verify route responses. Mock API services to avoid live API calls.
- **Coverage target:** Start with critical paths (auth, caching, dimension detail routes).

**Complexity: Medium** — Requires test infrastructure setup; time investment scales with coverage goals.

---

### 8. Documentation Improvements

**Goal:** Continue improving documentation for setup, deployment, and contribution.

**Why:** Good documentation reduces support burden and makes the project more accessible to new users and contributors.

**Items:**
- Add a `CONTRIBUTING.md` guide.
- Document the architecture in more detail (service layer, caching strategy, API fallback logic).
- Add troubleshooting guides for common deployment issues.
- Keep quick-start guides up to date with any v3 changes.

**Complexity: Low** — Ongoing effort throughout v3 development.

---

### 9. Configuration Change Detection

**Goal:** Detect and surface changes to Adobe Analytics configuration between cache refreshes — for example, when an eVar's name, allocation, or expiration changes, or when a new event is enabled.

**Why:** Adobe Analytics configurations are modified in the Admin Console and changes are not versioned or audited natively. Analysts often discover unexpected changes only when reports break. Codex already fetches configuration data on a 24-hour schedule; comparing consecutive snapshots is a natural extension.

**How:**
1. When the cache warmer writes a new snapshot, compare it against the previous snapshot for key fields (name, type, allocation, expiration, enabled state).
2. Store a diff log as a lightweight JSON file alongside the cache.
3. Surface detected changes on the Overview page as a "Recent Changes" panel with timestamps.

**Complexity: Medium** — Cache write logic is in `cache_warmer.py`. The diff logic is straightforward; the main effort is in deciding which fields to watch and presenting diffs readably.

---

### 10. Implementation Health Scorecard

**Goal:** Extend the Overview page with an actionable health report: unused variables (no data in the last 30 days), variables missing names or notes, duplicate display names, and classification coverage.

**Why:** The Overview page already aggregates counts and cache status. A health scorecard adds qualitative insight — flagging variables that should probably be decommissioned, or names that are too generic to be useful. This is the kind of documentation audit that currently has to be done manually.

**How:**
1. Use the Reporting API (`get_dimension_trend`) to check which variables have had zero traffic in the last 30 days.
2. Cross-reference with the notes service to identify variables with no `plain_description`.
3. Render flagged items as collapsible warning panels on the Overview page, grouped by severity.

**Complexity: Medium** — Requires Reporting API calls for each variable type (could be slow on large report suites); results should be cached separately with a longer TTL (e.g., 48 hours) since they are expensive to compute.

---

### 11. Export Enhancements

**Goal:** Offer a single-click export of all listing pages as a multi-sheet Excel workbook, and improve the print layout of detail pages for documentation and audit sharing.

**Why:** The current CSV exports are one-per-section and require multiple clicks to compile a full configuration snapshot. A combined Excel workbook (one sheet per dimension type) is the format most commonly expected in audit documents and handover packs.

**How:**
1. Add an `openpyxl` (or `xlsxwriter`) dependency to generate `.xlsx` files server-side.
2. Add a `/export/full` route that compiles all dimension types into a single workbook.
3. Add `@media print` CSS to detail page templates for clean printed output.

**Complexity: Low** — Data already exists in memory from existing export routes; the main effort is wiring up the new library and adding one combined route.

---

### 12. HTTP Security Hardening

**Goal:** Protect write routes (notes and tags POST/DELETE endpoints) against CSRF attacks, and add standard HTTP security response headers to all routes.

**Why:** Currently no security headers are set (Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Referrer-Policy) and the write API routes (`/api/notes`, `/api/tags`) have no CSRF protection. While the app is typically deployed internally, hardening against these vectors is low-cost and good practice — especially if User OAuth Login (v3-001) brings broader access.

**How:**
1. Add `Flask-Talisman` (or equivalent) to inject security headers on every response.
2. Add CSRF token validation to all non-GET routes using `Flask-WTF` or a lightweight token-in-header pattern.
3. Scope the Content-Security-Policy to permit the CDN sources currently used (Bootstrap, DataTables, Chart.js), or resolve after Self-Hosted Assets (v3-006).

**Complexity: Medium** — Straightforward for headers; CSRF requires care around the JavaScript-driven API routes that use `fetch()`.

---

### 13. Health Check Endpoint

**Goal:** Add a `/health` JSON endpoint that reports application status for container orchestration and uptime monitoring.

**Why:** Docker and Kubernetes use health probes to decide when to restart a container. Without a `HEALTHCHECK` instruction or readiness probe, a container that has booted but is broken (e.g., missing config, failed cache warmer) is indistinguishable from a healthy one. External uptime monitors also benefit from a status endpoint.

**How:**
1. Add a `GET /health` route (no client prefix — global) that returns `{"status": "ok", "version": "..."}`.
2. Optionally include cache status (last warmed timestamp) and API reachability (ping Adobe IMS).
3. Add `HEALTHCHECK CMD curl --fail http://localhost:5010/health` to the Dockerfile.

**Complexity: Low** — Simple route addition; the optional API ping should be non-blocking to avoid slow health checks causing false failures.

---



These items were identified in [autopsy 035](autopsies/035-pre-launch-architecture-review.md) but deferred:

| Item | Description | When to address |
|------|-------------|----------------|
| Template consolidation | `detail.html`, `event_detail.html`, `listvar_detail.html` are ~75% identical | When adding new detail page features |
| Route file split | `main.py` is ~2,700 lines; split into blueprints | After User OAuth adds `auth.py` pattern |
| Inline CSS extraction | Move `base.html` inline styles to `static/css/style.css` | Any quiet period |
| Cache file locking | Add file locking to `CacheService` to prevent race conditions | If usage increases |

---

*Last updated: 2026-04-22 (v3-001 revised — hybrid auth architecture after Reactor OAuth constraint discovered)*
