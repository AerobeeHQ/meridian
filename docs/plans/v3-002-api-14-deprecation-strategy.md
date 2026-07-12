# Plan: API 1.4 Deprecation Strategy

**Roadmap item:** Develop a plan for dealing with the shutdown of Adobe Analytics API v1.4 (scheduled August 2026).

**Complexity: High**

---

## Summary

Adobe is retiring API 1.4 in August 2026. Meridian currently uses API 1.4 for five feature areas: Processing Rules, Marketing Channels, Channel Rules, ListVars, and partial eVar configuration. This plan inventories the dependencies, evaluates mitigation options, and proposes a phased approach.

---

## Current API 1.4 Dependencies

### Service Layer (`app/services/adobe_analytics.py`)

| Method | API 1.4 Endpoint | Data Returned |
|--------|------------------|---------------|
| `get_processing_rules(rsid)` | `ReportSuite.ViewProcessingRules` | Conditions, actions, comments for each rule |
| `get_marketing_channels(rsid)` | `ReportSuite.GetMarketingChannels` | Channel names, colors, enabled state |
| `get_marketing_channel_rules(rsid)` | `ReportSuite.GetMarketingChannelRules` | Rule conditions, query params, operators |
| `get_list_variables(rsid)` | `ReportSuite.GetListVariables` | Name, allocation, expiration, delimiter, max values |
| `get_evars(rsid)` / `get_evar(rsid, id)` | `ReportSuite.GetEvars` | Allocation, expiration, merchandising syntax, binding events |

### Route Usage (`app/routes/main.py`)

| Route | API 1.4 Method | Purpose |
|-------|----------------|---------|
| `/<client>/processing-rules` | `get_processing_rules` | Listing page |
| `/<client>/processing-rules/export` | `get_processing_rules` | CSV export |
| `/<client>/marketing-channels` | `get_marketing_channels` | Listing page |
| `/<client>/marketing-channels/export` | `get_marketing_channels` | CSV export |
| `/<client>/channel-rules` | `get_marketing_channel_rules` | Listing page |
| `/<client>/channel-rules/export` | `get_marketing_channel_rules` | CSV export |
| `/<client>/listvars` | `get_list_variables` | Listing page |
| `/<client>/listvars/export` | `get_list_variables` | CSV export |
| `/<client>/listvars/<name>` | `get_list_variables` | Detail page |
| `/<client>/evars/<id>` | `get_evar` | Detail page (allocation, expiration, merchandising) |
| `/<client>/debug/call` | `_make_request` | API debug proxy |

### Cache Warmer (`app/services/cache_warmer.py`)

The background cache warmer pre-fetches these keys using API 1.4:
- `processing_rules`
- `channel_rules`
- `marketing_channels`
- `listvars`

---

## Mitigation Status by Feature

### ✅ eVar Configuration (Already Mitigated)

**Status:** Partial mitigation implemented in [autopsy 017](../autopsies/017-merchandising-evar-expiration-bug.md).

eVar allocation and expiration are now parsed from the API 2.0 `description` field, which embeds this metadata as structured text:
```
Expiration: Purchase.
Allocation: Merchandising (Last)
```

API 1.4 is still used as a **fallback** for:
- `merchandising_syntax` (Product Syntax vs Conversion Variable Syntax)
- `binding_events` (for Conversion Variable Syntax merchandising)
- Edge cases where description metadata is missing

**Post-deprecation impact:** Minor. Merchandising syntax detail may show "N/A" for some eVars; core allocation/expiration will continue working.

---

### ⚠️ ListVars Configuration (Partial API 2.0 Coverage)

**Current data source:** API 1.4 `ReportSuite.GetListVariables`

**API 2.0 coverage:** The `/dimensions` endpoint includes `variables/listvar1`, `variables/listvar2`, `variables/listvar3` with:
- ✅ `name` (display name)
- ✅ `id` (dimension ID)
- ✅ `description`
- ❌ `allocation` (not available)
- ❌ `expiration_type` / `expiration_custom_days` (not available)
- ❌ `delimiter` (not available)
- ❌ `max_values` (not available)

**Mitigation options:**
1. **Accept partial data loss** — Use API 2.0 dimensions; show "N/A" for missing config fields.
2. **Parse from description** — If Adobe populates listvar descriptions with metadata (like eVars), extract it.
3. **Manual upload** — Allow users to upload listvar config JSON.

**Recommendation:** Option 1 (partial data loss) with Option 3 (manual upload) as enhancement.

---

### ❌ Processing Rules (No API 2.0 Equivalent)

**Current data source:** API 1.4 `ReportSuite.ViewProcessingRules`

**API 2.0 coverage:** None. Processing rules are not exposed in API 2.0.

**Adobe UI export:** None. The Admin Console does not offer a "Download Rules" feature.

**Mitigation options:**
1. **Manual JSON upload** — User pastes/uploads a JSON snapshot extracted from a prior API 1.4 cache or manually constructed.
2. **Screenshot/manual entry** — User documents rules outside Meridian. (Unacceptable UX.)
3. **Browser automation** — Playwright script logs in and scrapes the Admin Console. (High complexity, fragile.)
4. **Feature deprecation** — Remove Processing Rules feature post-August 2026.

**Recommendation:** Option 1 (manual JSON upload) with Option 4 (graceful deprecation) as fallback.

---

### ❌ Marketing Channels (No API 2.0 Equivalent)

**Current data source:** API 1.4 `ReportSuite.GetMarketingChannels`

**API 2.0 coverage:** None. Marketing channel configuration is not exposed in API 2.0.

**Adobe UI export:** None.

**Mitigation options:** Same as Processing Rules.

**Recommendation:** Option 1 (manual JSON upload) with Option 4 (graceful deprecation) as fallback.

---

### ❌ Channel Rules (No API 2.0 Equivalent)

**Current data source:** API 1.4 `ReportSuite.GetMarketingChannelRules`

**API 2.0 coverage:** None.

**Adobe UI export:** None.

**Mitigation options:** Same as Processing Rules.

**Recommendation:** Option 1 (manual JSON upload) with Option 4 (graceful deprecation) as fallback.

---

## Gaps in Current Analysis

The sections below document gaps and alternative approaches not fully explored in the initial draft.

---

### Gap 1: Adobe Admin Console API (Not Investigated)

The v3 roadmap listed "Adobe Admin Console API" as option #3, but this plan does not analyse it. Adobe exposes some report suite configuration via the **Adobe Experience Cloud Admin APIs** (separate from the Analytics reporting API). The specific surface area needs a research spike:

- **Identity and access provisioning** is available via `https://usermanagement.adobe.io`
- **Report suite metadata** may be accessible via the Analytics Company API or a segment of the Experience Platform APIs
- **Processing rules and marketing channels** have never been confirmed as absent from all Adobe APIs — only from the Analytics 2.0 reporting surface

**Action required:** File an Adobe Developer support request and check the [Adobe Analytics Admin API Explorer](https://adobedocs.github.io/analytics-2.0-apis/) for any undocumented `/admin/` or `/reportsuite/` endpoints before writing off this option. If Adobe's migration guide for API 1.4 (expected mid-2026) is published, it should be reviewed immediately.

---

### Gap 2: AI-Assisted Configuration Extraction

The roadmap mentions an "AI agent that logs in and extracts configuration data." The plan dismisses this as "Playwright browser automation — High complexity, fragile." This conflates two distinct approaches:

| Approach | Complexity | Reliability | Description |
|----------|------------|-------------|-------------|
| DOM scraping (Playwright) | High | Low | Parses Admin Console DOM; breaks on UI changes |
| **AI vision + screenshot** | Medium | Medium | User takes a screenshot; an LLM with vision extracts structured data |
| **LLM-assisted copy-paste** | Low | High | User copies visible text from Admin Console; Claude parses it into JSON |

The third approach — a guided copy-paste flow where users paste raw text and an LLM normalises it into the expected schema — is low-risk and low-cost. It removes the burden of knowing the exact JSON format while still producing an uploadable file.

**Recommendation:** Add an optional "Paste & Extract" UI to the upload flow (Phase 2 enhancement) using an Adobe I/O or external LLM API. Treat as **opt-in** since it requires an additional API key.

---

### Gap 3: Cache Freeze Strategy

This is the most critical unaddressed risk. The current cache has:
- **1-hour TTL** for most API responses
- **24-hour TTL** for dimension/event configs

After August 2026, every cache expiry will trigger an API 1.4 call that fails. If the user has not uploaded a snapshot, the feature will show an error. But if the user _has_ the data in cache right before the deadline, that cache could be **frozen indefinitely** with a simple change:

**Proposed approach:** Add a `frozen_cache/` directory alongside `cache/`. When Phase 5 (pre-deprecation snapshot) is executed, copy the 1.4 cache keys to `frozen_cache/`. Post-deprecation, modify the service layer to check `frozen_cache/` before attempting a live API 1.4 call — and never expire those entries. This gives users a seamless zero-action fallback, compared to requiring an explicit upload.

**Implementation delta from current plan:**
1. `CacheService.freeze(rsid, key)` — copies a cache entry to `frozen_cache/` with no TTL
2. A "Freeze Cache" button in Settings (distinct from the ZIP download in Phase 5)
3. `AdobeAnalyticsService._make_request()` — check `frozen_cache/` before live call

This approach is strictly additive to Phase 5 and costs ~30 lines of code.

---

### Gap 4: API 1.4 End-of-Life Detection

The plan assumes API 1.4 will be "unavailable" after August 2026, but doesn't specify how Meridian will distinguish:

| Scenario | Current behaviour | Desired behaviour |
|----------|-------------------|-------------------|
| Temporary outage | Retry across 4 endpoints, then `RuntimeError` | Same |
| Permanent 410/403 from Adobe | Same as outage | Treat as deprecated; show upload CTA |
| Credential expired (unrelated) | Same as outage | Show credential error, not upload CTA |

**Recommendation:** Inspect the HTTP status code and response body before triggering the deprecation fallback. A `410 Gone` or an Adobe-issued deprecation notice in the error body should set a persistent flag (stored in `cache/<rsid>/api14_deprecated.json`) that suppresses further live calls and shows the "data unavailable" UI immediately rather than after all retry attempts fail.

---

### Gap 5: Stale Snapshot Governance

Once a user uploads a processing rules snapshot, there is no mechanism to:
1. Know when the underlying Adobe Analytics rules were last changed
2. Be warned that the uploaded snapshot may be out of date
3. Re-upload after a change is made in the Admin Console

**Recommendations:**
- Store an `uploaded_at` timestamp alongside each uploaded snapshot
- Surface "Snapshot uploaded {N} days ago" in the deprecation banner
- Add a `Last refreshed from live API: {date}` annotation so users know which data is from a frozen cache vs a manual upload
- Consider a quarterly reminder prompt in the UI if the snapshot is older than 90 days

---

### Gap 6: Phase Ordering — Phase 5 Should Be Phase 0

**Phase 5 (Pre-Deprecation Cache Snapshot)** is the most time-sensitive action in this entire plan — it must be completed before August 2026 or the opportunity to capture live data is permanently lost. Yet it is listed last.

**Revised priority:**

| Phase | Original # | Name | Deadline |
|-------|------------|------|---------|
| 0 | 5 | Pre-Deprecation Snapshot Download | **May 2026 — hard deadline** |
| 1 | 1 | Deprecation Warning Banner | May 2026 |
| 2 | 2 | Manual JSON Upload | June 2026 |
| 3 | 3 | ListVars API 2.0 Fallback | June 2026 |
| 4 | 4 | Graceful Degradation | July 2026 |

Implementing Phase 0 (formerly Phase 5) first also generates the reference JSON format that will be used as the upload schema in Phase 2 — reducing the risk of schema mismatch.

---

### Gap 7: Multi-Suite Deployments

The plan assumes a single report suite per Meridian client. In practice, some deployments run with multiple report suites per client (e.g., dev/staging/prod rollup). The upload and freeze workflow must handle:

- Per-RSID snapshot storage (already implied by `secrets/<client>/` structure)
- A bulk snapshot download that loops over all configured RSIDs
- Clear labelling of which RSID a snapshot belongs to in the Settings UI

---

### Gap 8: Security Implications of User-Uploaded JSON

Phase 2 introduces a file upload route that stores user-supplied JSON in `secrets/<client>/`. The plan mentions schema validation but does not address:

- **Path traversal**: A crafted filename in a multipart upload could escape the `secrets/<client>/` directory. Mitigation: use a fixed server-side filename (e.g., `processing_rules.json`), never use user-provided filenames.
- **JSON bomb / large payload**: Unbounded file size could exhaust memory during parsing. Mitigation: enforce a `MAX_CONTENT_LENGTH` limit on upload routes (e.g., 1 MB).
- **Code injection via JSON content**: Since the JSON is only read by the service layer and rendered in templates via Jinja2 auto-escaping, this risk is low — but note that any future `eval()`-style usage would be dangerous.

These mitigations should be part of the Phase 2 implementation checklist, not an afterthought.

---

### Gap 9: Adobe's Own Migration Path

Adobe typically publishes a migration guide when retiring a major API. This plan was written before that guide is available. When Adobe publishes migration guidance for API 1.4 to 2.0, it should be reviewed immediately and this document updated. Key questions to track:

- Will Adobe provide a one-time export tool for report suite configuration?
- Will any API 1.4 endpoints be ported to 2.0 before retirement?
- Are there enterprise agreements that extend API 1.4 access beyond August 2026?
- Does Adobe's Customer Journey Analytics (CJA) expose equivalent configuration APIs?

**Action:** Subscribe to Adobe Analytics developer release notes. Add a calendar reminder for Q2 2026 to check for migration guidance.

---

## Implementation Plan

### Phase 0: Pre-Deprecation Snapshot & Cache Freeze (⚠️ Hard deadline: May 2026)

**Goal:** Before August 2026, capture a complete API 1.4 snapshot while data is still retrievable. This is the single most time-critical action in this plan; all other phases depend on having a snapshot to fall back to.

**Implementation:**
1. Add a "Download Full Snapshot" button to the Settings page that generates a ZIP containing:
   - `processing_rules.json`
   - `marketing_channels.json`
   - `channel_rules.json`
   - `listvars.json`
2. Add a `CacheService.freeze(rsid, key)` method that copies a live cache entry to `frozen_cache/` with no TTL expiry, so data persists after August 2026 without user action.
3. Add a "Freeze Cache" action that calls `freeze()` for all API 1.4 keys across all configured RSIDs.
4. The downloaded ZIP and the frozen cache serve the same purpose via different workflows (download/re-upload vs automatic in-memory persistence).

**Why Phase 0 before Phase 1:** Implementing this first generates the reference JSON files that define the upload schema for Phase 2, reducing the risk of schema mismatch between download and re-upload.

**Files to change:**
- `app/services/cache.py` — add `freeze()` method, `frozen_cache/` read-before-live-call logic
- `app/routes/main.py` — snapshot download route, freeze action
- `app/templates/settings.html` — "Download Snapshot" + "Freeze Cache" buttons

---

### Phase 1: Deprecation Warning Banner (Low effort)

**Goal:** Inform users that API 1.4 features will stop updating after August 2026.

**Implementation:**
1. Add a `API_14_DEPRECATED` config flag (default `false`; set `true` after August 2026).
2. Add a warning banner to pages that rely on API 1.4 data:
   - Processing Rules listing
   - Marketing Channels listing
   - Channel Rules listing
   - ListVars listing/detail
3. Banner text: *"This data was last updated on {cache_date}. Adobe retired API 1.4 in August 2026; automatic updates are no longer available. [Upload snapshot](#) to refresh."*
4. If a snapshot was uploaded, show: *"Showing snapshot uploaded {N} days ago."* to make staleness visible.

**Files to change:**
- `app/templates/listing.html` — conditional banner
- `app/routes/main.py` — pass `api_14_deprecated` flag and snapshot metadata to template context

---

### Phase 2: Manual JSON Upload (Medium effort)

**Goal:** Allow users to upload a JSON snapshot of rules/channels/listvars configuration to replace or supplement API 1.4 data.

**Data model:**
```
secrets/<client>/
├── processing_rules.json      # User-uploaded snapshot
├── marketing_channels.json
├── channel_rules.json
└── listvars.json
```

**Implementation:**
1. Add upload routes:
   - `POST /<client>/settings/upload/processing-rules`
   - `POST /<client>/settings/upload/marketing-channels`
   - `POST /<client>/settings/upload/channel-rules`
   - `POST /<client>/settings/upload/listvars`
2. Validate uploaded JSON against expected schema (array of objects with required keys).
3. Store uploaded files in `secrets/<client>/` directory using a **fixed server-side filename** — never use user-provided filenames to prevent path traversal.
4. Enforce `MAX_CONTENT_LENGTH` of 1 MB on upload routes to prevent JSON bomb / memory exhaustion.
5. Modify service layer to check for uploaded file **first**, then fall back to frozen cache, then API 1.4 (if available).
6. Store an `uploaded_at` ISO timestamp in a sidecar `<type>_meta.json` file alongside each uploaded snapshot for staleness tracking.
7. Add download routes so users can export their current API 1.4 cache as the upload format:
   - `GET /<client>/settings/download/processing-rules`
   - etc.

**Files to change:**
- `app/routes/main.py` — upload/download routes
- `app/services/adobe_analytics.py` — add `load_from_file()` fallback logic, `frozen_cache` check
- `app/templates/settings.html` — upload UI section

**Schema example (processing_rules.json):**
```json
[
  {
    "ruleNum": 1,
    "title": "Set campaign eVar",
    "rules": "If Query String Parameter cid exists",
    "matchOn": "all",
    "actions": "Set eVar3 to Query String Parameter cid",
    "comment": "Campaign tracking"
  }
]
```

---

### Phase 3: ListVars API 2.0 Fallback (Low effort)

**Goal:** Use API 2.0 `/dimensions` data for ListVars when API 1.4 is unavailable.

**Implementation:**
1. Add `get_listvars_from_dimensions()` method to `AdobeAnalyticsV2Service`.
2. Modify `/listvars` route to try API 2.0 first (if uploaded file not present), then API 1.4.
3. Accept that `allocation`, `expiration`, `delimiter`, `max_values` will show "N/A" when sourced from API 2.0.

**Files to change:**
- `app/services/adobe_analytics_v2.py` — new method
- `app/routes/main.py` — fallback logic in `/listvars` routes

---

### Phase 4: Graceful Degradation with EOF Detection (Low effort)

**Goal:** After August 2026, routes that fail to fetch API 1.4 data should display an informative message instead of crashing. Importantly, Meridian must distinguish a permanent deprecation from a temporary outage.

**Implementation:**
1. Inspect HTTP status codes from API 1.4 responses:
   - `410 Gone` or Adobe-issued deprecation body → set a persistent `api14_deprecated.json` flag in `cache/<rsid>/`; suppress future live calls immediately
   - `401/403` → credential error, not deprecation; show credential fix prompt
   - `5xx` / network timeout → temporary outage; continue with existing retry logic
2. If the persistent deprecation flag is set and no fallback data (uploaded file or frozen cache) exists, render a "data unavailable" template with instructions.
3. Processing Rules, Channel Rules, and Marketing Channels routes should show: *"API 1.4 has been retired. Upload a configuration snapshot to view this data."*

**Files to change:**
- `app/routes/main.py` — error handling in affected routes
- `app/services/adobe_analytics.py` — EOF detection and persistent flag logic
- `app/templates/_api_14_retired.html` — new partial template

---

### Phase 5: Removed (Merged into Phase 0)

---

## Decisions Required

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Should we pursue DOM-scraping browser automation (Playwright)? | Yes / No / Defer | **Defer** — High complexity, fragile, security concerns. Revisit only if demand is high. |
| 2 | Should we file an Adobe feature request for 2.0 endpoints? | Yes / No | **Yes** — Low effort, unlikely to land before August 2026, but worth documenting. |
| 3 | Should the upload UI accept raw JSON only or also a guided form? | JSON-only / Guided form | **JSON-only for v3** — Guided form is v4+ polish. |
| 4 | Should we remove API 1.4 code after August 2026? | Remove / Keep as dead code | **Keep for 6 months** — Some enterprise customers may have extended API access. |
| 5 | Should we add an AI/LLM "Paste & Extract" flow to the upload UI? | Yes / No / Defer | **Defer** — Requires an additional API key and introduces an external dependency; revisit in v4. |
| 6 | Should we investigate Adobe Admin Console API for rules/channels data? | Yes / No | **Yes (research spike)** — File an Adobe Developer support request and review the API Explorer before August 2026. |
| 7 | Should the cache freeze happen automatically before expiry, or require a manual trigger? | Auto / Manual | **Manual for v3** — A one-click "Freeze Cache" button is lower-risk than background automation; auto-freeze can be added later. |

---

## Timeline

| Date | Milestone |
|------|-----------|
| **May 2026** | **Phase 0** (snapshot download + cache freeze) + **Phase 1** (deprecation banner) |
| **June 2026** | **Phase 2** (manual upload) + **Phase 3** (ListVars fallback) |
| **July 2026** | **Phase 4** (graceful degradation + EOF detection) + user communication |
| **August 2026** | API 1.4 retired — Meridian continues with frozen cache or uploaded snapshots |
| **September 2026** | Review: check whether Adobe published a migration guide or extended 1.4 access |
| **February 2027** | Evaluate removing API 1.4 code |

---

## Files to Change (Summary)

| File | Changes |
|------|---------|
| `app/routes/main.py` | Upload/download routes, fallback logic, error handling, freeze action |
| `app/services/adobe_analytics.py` | `load_from_file()` fallback, EOF detection, persistent deprecation flag |
| `app/services/adobe_analytics_v2.py` | `get_listvars_from_dimensions()` method |
| `app/services/cache.py` | `freeze()` method, `frozen_cache/` read-before-live-call logic |
| `app/templates/listing.html` | Deprecation warning banner with snapshot staleness info |
| `app/templates/settings.html` | Upload UI section, "Download Snapshot" and "Freeze Cache" buttons |
| `app/templates/_api_14_retired.html` | New template for graceful degradation |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users don't download/freeze snapshots before August 2026 | Medium | High | Proactive in-app warnings from May 2026; cache freeze is one-click |
| Uploaded JSON schema doesn't match expected format | Medium | Low | Schema validation on upload, fixed server-side filenames, clear error messages |
| Path traversal via upload filename | Low | High | Always use fixed server-side filenames; never use user-provided filenames |
| Large JSON upload exhausts server memory | Low | Medium | Enforce `MAX_CONTENT_LENGTH` 1 MB limit on upload routes |
| Adobe extends API 1.4 deadline | Low | Positive | No action needed; continue using API 1.4 |
| Adobe adds 2.0 endpoints for rules/channels | Low | Positive | Update Meridian to use new endpoints |
| API 1.4 EOF detection misidentifies outage as deprecation | Low | Medium | Only set persistent deprecated flag on `410 Gone`; retry on `5xx` as today |
| Uploaded snapshot is silently stale (rules changed post-upload) | Medium | Medium | Show `uploaded_at` timestamp in UI; add quarterly staleness prompt |
| Adobe Admin Console API research yields nothing actionable | Medium | Low | Treat as best-effort; does not block other phases |

---

## References

- [Autopsy 016: eVar Allocation and Expiration Fix](../autopsies/016-evar-allocation-expiration-fix.md)
- [Autopsy 017: Merchandising eVar Expiration Bug](../autopsies/017-merchandising-evar-expiration-bug.md)
- [Adobe Analytics API 1.4 Documentation](https://developer.adobe.com/analytics-apis/docs/1.4/)
- [Adobe Analytics API 2.0 Documentation](https://developer.adobe.com/analytics-apis/docs/2.0/)
- [Adobe Analytics API 2.0 Explorer](https://adobedocs.github.io/analytics-2.0-apis/) — check for undocumented admin endpoints
- [Adobe User Management API](https://developer.adobe.com/umapi/) — separate from Analytics APIs; investigate for config data

---

*Created: 2026-04-19 | Updated: 2026-04-19 (added gap analysis, alternative approaches, cache freeze strategy, EOF detection, phase reordering)*

