# Version 2 Roadmap

This document summarises the planned features for Codex v2. Each item has a detailed implementation plan in `docs/plans/`.

---

## Feature Overview

| # | Feature | Complexity | Status | Plan |
|---|---------|------------|--------|------|
| 1 | [Processing Rules Integration](#1-processing-rules-integration) | Medium | **Done** | [v2-001](plans/v2-001-processing-rules-integration.md) |
| 2 | [Marketing Channel Rules Integration](#2-marketing-channel-rules-integration) | Medium | Planned | [v2-002](plans/v2-002-marketing-channel-rules-integration.md) |
| 3 | [Adobe Launch Integration](#3-adobe-launch-integration) | High | Planned | [v2-003](plans/v2-003-adobe-launch-integration.md) |
| 4 | [User OAuth Login](#4-user-oauth-login) | High | Planned | [v2-004](plans/v2-004-user-oauth-login.md) |
| 5 | [Background Pre-Caching](#5-background-pre-caching) | Medium | **Done** | [v2-005](plans/v2-005-background-precaching.md) |
| 6 | [Report Suite Overview Page](#6-report-suite-overview-page) | Low–Medium | **Done** | [v2-006](plans/v2-006-report-suite-overview.md) |

---

## Suggested Implementation Order

Start with low-risk, high-value additions before architectural changes:

1. ~~**Overview page** (v2-006) — New page only, no risk to existing features.~~ **Done**
2. ~~**Background pre-caching** (v2-005) — Makes the whole app feel faster; improves UX for all users.~~ **Done**
3. ~~**Processing Rules integration** (v2-001) — Data already cached; adds cross-linking to detail pages.~~ **Done**
4. **Marketing Channel Rules integration** (v2-002) — Identical pattern to v2-001; reuses code.
5. **Adobe Launch integration** (v2-003) — New API client; higher effort, requires spike first.
6. **User OAuth login** (v2-004) — Largest architectural change; do last.

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
