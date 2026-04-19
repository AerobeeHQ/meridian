# Version 2 Roadmap

This document summarises the planned features for Codex v2. Each item has a detailed implementation plan in `docs/plans/`.

---

## Feature Overview

| # | Feature | Complexity | Status | Plan |
|---|---------|------------|--------|------|
| 1 | [Processing Rules Integration](#1-processing-rules-integration) | Medium | **Done** | [v2-001](plans/v2-001-processing-rules-integration.md) |
| 2 | [Marketing Channel Rules Integration](#2-marketing-channel-rules-integration) | Medium | **Done** | [v2-002](plans/v2-002-marketing-channel-rules-integration.md) |
| 3 | [Adobe Launch Integration](#3-adobe-launch-integration) | High | **Done** | [autopsy 036](autopsies/036-adobe-launch-integration.md) |
| 4 | [User OAuth Login](#4-user-oauth-login) | High | Scaffolded | [v2-004](plans/v2-004-user-oauth-login.md) |
| 5 | [Background Pre-Caching](#5-background-pre-caching) | Medium | **Done** | [v2-005](plans/v2-005-background-precaching.md) |
| 6 | [Report Suite Overview Page](#6-report-suite-overview-page) | Low–Medium | **Done** | [v2-006](plans/v2-006-report-suite-overview.md) |
| 7 | [Segments](#7-segments) | Low–Medium | **Done** | [autopsy 025](autopsies/025-segments.md) |
| 8 | [Calculated Metrics](#8-calculated-metrics) | Medium | **Done** | [autopsy 027](autopsies/027-calculated-metrics.md) |
| 9 | [Interactive API Debug Page](#9-interactive-api-debug-page) | Medium | **Done** | [autopsy 034](autopsies/034-api-debug-page.md) |
| 10 | [Themes & Settings Page](#10-themes--settings-page) | Low–Medium | In Progress | [v2-010](plans/v2-010-themes-settings.md) |

---

## Suggested Implementation Order

Start with low-risk, high-value additions before architectural changes:

1. ~~**Overview page** (v2-006) — New page only, no risk to existing features.~~ **Done**
2. ~~**Background pre-caching** (v2-005) — Makes the whole app feel faster; improves UX for all users.~~ **Done**
3. ~~**Processing Rules integration** (v2-001) — Data already cached; adds cross-linking to detail pages.~~ **Done**
4. ~~**Segments** (v2-007) — Listing and detail pages via API 2.0.~~ **Done**
5. ~~**Calculated Metrics** (v2-008) — Listing, detail pages, formula cross-references, and trend charts via API 2.0.~~ **Done**
6. ~~**Interactive API debug page** (v2-009) — Browser-based explorer for all 1.4 and 2.0 endpoints, proxied through the server.~~ **Done**
7. ~~**Marketing Channel Rules integration** (v2-002) — Identical pattern to v2-001; reuses code.~~ **Done**
8. ~~**Adobe Launch integration** (v2-003) — New API client; higher effort, requires spike first.~~ **Done**
9. **User OAuth login** (v2-004) — Largest architectural change. Config scaffolding is in place (`AUTH_MODE`, `OAUTH_REDIRECT_URI`, `SESSION_SECRET`); full per-user flow not yet implemented.

---

## Feature Details

### 1. Processing Rules Integration

**Goal:** On each Prop, eVar, Event, and ListVar detail page, show a list of Processing Rules that reference or modify that dimension.

**Why:** Analysts often need to understand not just what a variable is, but how it gets populated. Processing rules are the most common mechanism and are already fetched by the app.

**How:** Cross-reference the cached processing rules list against the current dimension name using string matching. Surface matches in a collapsible section on the detail page. No new API calls required.

**Complexity: Medium** — data already exists; effort is in the matching logic and UI additions.

---

### 2. Marketing Channel Rules Integration

**Goal:** On each detail page, show which Marketing Channel processing rules reference that dimension.

**Why:** Same rationale as Processing Rules — understanding data lineage.

**How:** Same pattern as v2-001, using the already-cached channel rules. Implement after v2-001 as the code is nearly identical.

**Complexity: Medium** — Note: a data inspection spike is needed first to confirm that channel rules reference custom variables in a cross-linkable way.

---

### 3. Adobe Launch Integration

**Goal:** On each detail page, show which Adobe Launch (Tags) rules set or alter that dimension.

**Why:** Launch is where variables are most commonly set at the collection layer. Surfacing Launch rules alongside the Analytics configuration gives a complete picture of how data flows from the browser to reporting.

**How:** Requires a new API client for the Adobe Reactor (Tags) API, new config fields, and a new cache layer. Re-uses the same detail page UI pattern as v2-001/v2-002.

**Complexity: High** — new API integration from scratch; requires a spike notebook to understand data shape; may require additional OAuth2 scopes.

See also this Github repo: https://github.com/maxisdigital/launchpad 

Let me know if you need access.

---

### 4. User OAuth Login

**Goal:** Replace the server-to-server credential model with individual user login via Adobe IMS OAuth.

**Why:** Enables per-user access control (users only see report suites they have access to), removes the need to share a service account credential, and is required if Codex is ever deployed for a wider audience.

**How:** Add an OAuth Authorization Code flow (login/callback/logout routes), Flask session management, and a `before_request` login guard. Keep server-to-server as the default; user auth is opt-in via `AUTH_MODE` config.

**Complexity: High** — touches auth, sessions, API calls, and deployment configuration. Requires Adobe I/O Console setup before coding begins.

---

### 5. Background Pre-Caching

**Goal:** Pre-warm the cache at startup and refresh it on a 24-hour schedule, so users never wait for a cold cache. Add a "Force Refresh" button on listing and detail pages.

**Why:** The current 1-hour cache means users occasionally hit a slow page. Configuration data (eVars, Props, Processing Rules) rarely changes and is safe to cache for 24 hours.

**How:** Add APScheduler (lightweight, in-process scheduler — no Redis/Celery needed), a `cache_warmer.py` service, a new `/cache/refresh/<key>` route, and a per-key TTL option in `CacheService`.

**Complexity: Medium** — new dependency and background thread, but no architectural changes.

---

### 6. Report Suite Overview Page

**Goal:** A landing page that shows a snapshot of the report suite: how many eVars/Props/Events are configured, processing rule count, cache status, and recent documentation activity.

**Why:** Gives analysts and managers a quick health-check view without drilling into individual dimensions.

**How:** New `/overview` route + template. Uses already-cached data — no new API calls. Aggregate counts, utilisation bars, mini cache status panel.

**Complexity: Low–Medium** — new page only; all data already exists in the cache. Lowest risk item in v2.

---

### 7. Segments

**Goal:** List all segments defined in the report suite and provide a detail page showing segment definition, containers, and referenced dimensions.

**Why:** Segments are a core building block in Adobe Analytics. Documenting them alongside variable configurations gives a more complete picture of the implementation.

**How:** Uses the API 2.0 `/segments` endpoint with `includeType=all` (required to return segments owned by the service account). Recursive formula walker parses container trees into human-readable cross-references.

**Complexity: Low–Medium** — straightforward API 2.0 endpoint; complexity is in parsing the nested segment definition JSON.

---

### 8. Calculated Metrics

**Goal:** List all calculated metrics with type, owner, and tags. Detail page shows formula cross-references, a 30-day trend chart, and the raw formula JSON.

**Why:** Calculated metrics built on top of standard events are often poorly documented. Surfacing their formula components alongside the referenced events and segments closes a common knowledge gap.

**How:** Uses the API 2.0 `/calculatedmetrics` endpoint with `includeType=all`. Formula is parsed by a recursive tree walker to extract referenced `metrics/` and `segment-ref` nodes. Trend data is fetched via the Reporting API.

**Complexity: Medium** — formula parsing requires recursive traversal of an arbitrary-depth JSON tree; trend chart reuses the existing Chart.js pattern from Events.


### 9. Interactive API Debug Page

**Goal:** A browser-based explorer for all Adobe Analytics API 1.4 and 2.0 endpoints, accessible at `/debug`. Users can browse endpoints by tag, inspect parameters, and execute read-only requests without leaving the app.

**Why:** Debugging API calls or exploring what an endpoint returns previously required switching to Postman or a Jupyter notebook and re-entering credentials. Having this capability built into the app accelerates development and gives analysts direct visibility into the raw API data.

**How:** Both Swagger specs bundled in `docs/` are parsed at startup into a flat list of endpoint descriptors. The debug page receives this list as inline JSON and renders a two-panel layout — endpoint browser on the left, request/response editor on the right. All API calls are proxied through a `/debug/call` Flask endpoint, keeping credentials server-side and avoiding CORS. Write methods (POST, PUT, DELETE, PATCH) are disabled both in the UI and at the server layer.

**Complexity: Medium** — no new API client needed; effort is in the Swagger parsing (including `$ref` resolution for 1.4) and the single-page JS UI.

**See:** [autopsy 034](autopsies/034-api-debug-page.md)

---

### 10. Themes & Settings Page

**Goal:** Allow users to choose a UI theme (System/Light/Dark) via a Settings page, with dark mode auto-applied for browsers that prefer it. Planned themes include a future Adobe Spectrum theme.

**Why:** Dark mode is a common accessibility and comfort preference. A Settings page gives users control over the app's appearance without requiring configuration changes. Adobe Spectrum will align the app's design language with Adobe's own tools.

**How:**
- Theme preference is persisted in `localStorage` as `codex-theme` (`auto`, `light`, `dark`; future: `spectrum`).
- Bootstrap 5.3's `data-bs-theme` attribute is applied to `<html>` at load time via an inline script in `<head>` (prevents flash of unstyled content).
- In `auto` mode, the resolved theme follows `prefers-color-scheme` and updates dynamically if the OS theme changes.
- A new `/settings` route and `settings.html` template provides a theme selector UI.
- A settings icon in the navbar right-side links to the settings page.
- Adobe Spectrum theme is scaffolded as a future option using `@adobe/spectrum-web-components`.

**Complexity: Low–Medium** — no API changes needed; all state is client-side. Bootstrap 5.3 dark mode handles most component styling automatically; only a handful of custom CSS properties need explicit dark overrides.
