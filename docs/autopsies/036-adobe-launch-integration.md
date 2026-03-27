# Autopsy 036 — Adobe Launch Integration (v2-003)

**Date:** 2026-03-27
**Branch:** `feature/v2-003-adobe-launch-integration`
**Status:** Complete — merged

---

## Summary

Implemented Roadmap item v2-003: surface Adobe Experience Platform Tags (Launch) Set Variables rules on Prop, eVar, Event, and ListVar detail pages. Each detail page now shows which Launch rules set that dimension, with optional deep-links into the Launchpad app.

---

## Context

Adobe Launch is where Analytics variables are most commonly populated at the collection layer. Before this feature, Codex showed what a variable *is* (configuration) but not *how it gets set* (collection). v2-003 closes that gap.

The implementation was informed by the existing [Launchpad](../../../Launchpad) codebase and its autopsies, which documented the Reactor API's data quirks.

---

## Architecture

### New service: `app/services/adobe_launch.py`

`AdobeLaunchService` is a direct HTTP client for the Reactor API — no third-party library dependency. It:

1. Fetches all rules for a property (`GET /properties/{id}/rules`, paginated)
2. Fetches rule components in parallel (`GET /rules/{id}/rule_components`, 8 workers)
3. Filters to `adobe-analytics::actions::setVariables` delegate descriptor IDs
4. Parses settings JSON → compact action dicts with `evars`, `props`, `events`, `lists` lists

### Cache key: `launch_rules`

Added to `CONFIG_CACHE_KEYS` alongside `processing_rules`. The cache warmer only populates it when `codex_launch_service` is present on the app (i.e., when `LAUNCH_ENABLED` is true and `LAUNCH_PROPERTY_ID` is configured).

### Cross-reference: `find_related_launch_rules()`

Added to `main.py` alongside `find_related_processing_rules()`. Strips the alphabetic prefix from a dimension ID (e.g. `evar5` → `5`) and does case-insensitive matching against the cached action lists.

### Fragment endpoint and UI

Same async fragment pattern as processing rules:
- `/api/related-launch-rules/<dimension_type>/<dimension_id>` returns an HTML card
- Returns `204 No Content` when `LAUNCH_ENABLED` is false (placeholder removes itself)
- `detail.html`, `event_detail.html`, `listvar_detail.html` have a `{% if config.LAUNCH_ENABLED %}` guarded placeholder and JS fetch block
- Macro `related_launch_rules_section` renders rule names as links to Launchpad if `LAUNCHPAD_URL` is configured

### Auth: separate `OAuth2Auth` instance

The Reactor API requires broader IMS scopes than Analytics alone. A dedicated `OAuth2Auth` instance is created at startup so the narrower Analytics token cache is not affected.

**Required scopes** (matched to what launchpy uses successfully):
```
AdobeID, openid, read_organizations, additional_info.job_function,
additional_info.projectedProductContext, additional_info.roles
```

These can be overridden with the `LAUNCH_SCOPES` config field.

**Adobe Developer Console prerequisite:** The **Experience Platform Launch API** must be explicitly added to the project, with a product profile that grants property access (e.g. *Launch — All Properties*). Projects that only have Adobe Analytics configured will receive 403 on all Reactor API calls, even if the credentials are otherwise valid. This is the most common setup error.

---

## Key Learnings from Launchpad

These were documented in the Launchpad autopsies and confirmed during implementation:

| Finding | Impact |
|---------|--------|
| Reactor API returns `settings` as a **JSON string**, not a parsed object | Must always `json.loads()` — direct dict access raises `AttributeError` |
| Two settings formats exist: `{"trackerProperties": {"eVars": [...]}}` (modern) and `{"eVars": [...]}` (legacy) | Service tries `trackerProperties` wrapper first, falls back to direct keys |
| eVar names use capital V: `eVar1`, not `evar1` | `find_related_launch_rules` builds target as `eVar{N}` for evar lookups; matching is case-insensitive |
| Large properties can have hundreds of rules | Rule components are fetched with `ThreadPoolExecutor(max_workers=8)` |
| `links.next` in the response body is the pagination cursor | `_get_all_pages()` follows `links.next` until `None` |

---

## Configuration

Three new/updated config fields:

| Field | Default | Purpose |
|-------|---------|---------|
| `LAUNCH_ENABLED` | `false` | Master switch — was already present from autopsy 035 |
| `LAUNCH_PROPERTY_ID` | `""` | Reactor property ID (`PR...`) — was already present |
| `LAUNCHPAD_URL` | `""` | Base URL of the Launchpad app for deep links (new in this PR) |

The `SCOPES` field for the Analytics API does **not** need to include the Reactor scope. The service automatically appends it to a dedicated auth instance.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/adobe_launch.py` | **New** — `AdobeLaunchService` Reactor API client |
| `app/templates/_fragment_related_launch_rules.html` | **New** — async HTML fragment template |
| `config.dist.json` | Added `LAUNCHPAD_URL`; updated `_comment_launch` |
| `app/__init__.py` | Load `LAUNCHPAD_URL`; instantiate `AdobeLaunchService` |
| `app/services/cache_warmer.py` | Add `launch_rules` cache key; populate when service present |
| `app/routes/main.py` | `find_related_launch_rules()` + `/api/related-launch-rules/` endpoint |
| `app/templates/_macros.html` | `related_launch_rules_section` macro |
| `app/templates/detail.html` | Launch placeholder + JS |
| `app/templates/event_detail.html` | Launch placeholder + JS |
| `app/templates/listvar_detail.html` | Launch placeholder + JS |

---

## Known Limitations

- **Custom code actions excluded:** Variables set via `core::actions::custom-code` (JavaScript) are not detected, since the code is stored as a freeform string and would require regex analysis. This is a potential false negative (a rule sets the variable but Codex doesn't show it). A future enhancement could do regex-based matching against the `source` string as a fallback.
- **listvar support unconfirmed:** The `list1`/`list2`/`list3` variable names under a `lists` key in the settings are assumed based on the known eVar/prop/event pattern. This may need adjustment after inspecting real list variable data in the Reactor API.
- **Adobe Analytics Mobile extension:** The filter checks for `adobe-analytics` in the delegate descriptor ID. The mobile extension uses a different ID prefix and is not captured. This is an intentional scope limit for the initial implementation.
