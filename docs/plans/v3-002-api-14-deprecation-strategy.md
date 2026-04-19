# Plan: API 1.4 Deprecation Strategy

**Roadmap item:** Develop a plan for dealing with the shutdown of Adobe Analytics API v1.4 (scheduled August 2026).

**Complexity: High**

---

## Summary

Adobe is retiring API 1.4 in August 2026. Codex currently uses API 1.4 for five feature areas: Processing Rules, Marketing Channels, Channel Rules, ListVars, and partial eVar configuration. This plan inventories the dependencies, evaluates mitigation options, and proposes a phased approach.

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
2. **Screenshot/manual entry** — User documents rules outside Codex. (Unacceptable UX.)
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

## Implementation Plan

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

**Files to change:**
- `app/templates/listing.html` — conditional banner
- `app/routes/main.py` — pass `api_14_deprecated` flag to template context

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
3. Store uploaded files in `secrets/<client>/` directory.
4. Modify service layer to check for uploaded file **first**, then fall back to API 1.4 (if available).
5. Add download routes so users can export their current API 1.4 cache as the upload format:
   - `GET /<client>/settings/download/processing-rules`
   - etc.

**Files to change:**
- `app/routes/main.py` — upload/download routes
- `app/services/adobe_analytics.py` — add `load_from_file()` fallback logic
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

### Phase 4: Graceful Degradation (Low effort)

**Goal:** After August 2026, routes that fail to fetch API 1.4 data should display an informative message instead of crashing.

**Implementation:**
1. Wrap API 1.4 calls in try/except; catch connection errors and API errors.
2. If API 1.4 fails and no uploaded file exists, render a "data unavailable" template with instructions.
3. Processing Rules, Channel Rules, and Marketing Channels routes should show: *"API 1.4 has been retired. Upload a configuration snapshot to view this data."*

**Files to change:**
- `app/routes/main.py` — error handling in affected routes
- `app/templates/_api_14_retired.html` — new partial template

---

### Phase 5: Pre-Deprecation Cache Snapshot (Low effort, time-sensitive)

**Goal:** Before August 2026, prompt users to download a full cache snapshot while API 1.4 is still available.

**Implementation:**
1. Add a "Download Full Cache" button to the Settings page.
2. Generates a ZIP file containing:
   - `processing_rules.json`
   - `marketing_channels.json`
   - `channel_rules.json`
   - `listvars.json`
3. Users can re-upload these files after API 1.4 is retired.

**Timeline:** Must be implemented and communicated to users **before August 2026**.

---

## Decisions Required

| # | Question | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | Should we pursue browser automation (Playwright)? | Yes / No / Defer | **Defer** — High complexity, fragile, security concerns. Revisit only if demand is high. |
| 2 | Should we file an Adobe feature request for 2.0 endpoints? | Yes / No | **Yes** — Low effort, unlikely to land before August 2026, but worth documenting. |
| 3 | Should the upload UI accept raw JSON only or also a guided form? | JSON-only / Guided form | **JSON-only for v3** — Guided form is v4+ polish. |
| 4 | Should we remove API 1.4 code after August 2026? | Remove / Keep as dead code | **Keep for 6 months** — Some enterprise customers may have extended API access. |

---

## Timeline

| Date | Milestone |
|------|-----------|
| **May 2026** | Phase 1 (deprecation banner) + Phase 5 (pre-deprecation snapshot download) |
| **June 2026** | Phase 2 (manual upload) + Phase 3 (ListVars fallback) |
| **July 2026** | Phase 4 (graceful degradation) + user communication |
| **August 2026** | API 1.4 retired — Codex continues with uploaded snapshots |
| **February 2027** | Evaluate removing API 1.4 code |

---

## Files to Change (Summary)

| File | Changes |
|------|---------|
| `app/routes/main.py` | Upload/download routes, fallback logic, error handling |
| `app/services/adobe_analytics.py` | `load_from_file()` fallback, error handling |
| `app/services/adobe_analytics_v2.py` | `get_listvars_from_dimensions()` method |
| `app/templates/listing.html` | Deprecation warning banner |
| `app/templates/settings.html` | Upload UI section |
| `app/templates/_api_14_retired.html` | New template for graceful degradation |

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users don't download snapshots before August 2026 | Medium | High | Proactive communication, in-app warnings starting May 2026 |
| Uploaded JSON schema doesn't match expected format | Medium | Low | Schema validation on upload, clear error messages |
| Adobe extends API 1.4 deadline | Low | Positive | No action needed; continue using API 1.4 |
| Adobe adds 2.0 endpoints for rules/channels | Low | Positive | Update Codex to use new endpoints |

---

## References

- [Autopsy 016: eVar Allocation and Expiration Fix](../autopsies/016-evar-allocation-expiration-fix.md)
- [Autopsy 017: Merchandising eVar Expiration Bug](../autopsies/017-merchandising-evar-expiration-bug.md)
- [Adobe Analytics API 1.4 Documentation](https://developer.adobe.com/analytics-apis/docs/1.4/)
- [Adobe Analytics API 2.0 Documentation](https://developer.adobe.com/analytics-apis/docs/2.0/)

---

*Created: 2026-04-19*

