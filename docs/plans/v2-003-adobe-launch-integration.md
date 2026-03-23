# Plan: Adobe Launch (Tags) Integration on Detail Pages

**Roadmap item:** When viewing a Prop, eVar, Event, or ListVar, show which Adobe Launch (Tags) rule sets or alters that dimension.

**Complexity: High**

---

## Overview

This is the highest-effort item in the v2 roadmap. Adobe Launch (now called Adobe Experience Platform Tags) is an entirely separate product with its own REST API, authentication, and data model. Unlike the Processing Rules integration (which uses already-cached data), this requires building a new API client, new auth credentials, and new caching layer from scratch.

---

## What Adobe Launch Is

Adobe Experience Platform Tags (formerly Launch, formerly DTM) is a tag management system. It contains **Rules** — each rule has:
- **Conditions:** when to fire (page load, click, custom event, etc.)
- **Actions:** what to do (set an Adobe Analytics variable, send a beacon, etc.)

The Actions are what's relevant: an action might say "Set eVar5 = page name" or "Set event2 = 1". These are the mappings we want to surface on detail pages.

---

## API Overview

Adobe Experience Platform Tags uses the **Reactor API** (separate from Analytics API):
- Base URL: `https://reactor.adobe.io`
- Authentication: Adobe IMS OAuth2 (same `CLIENT_ID`/`CLIENT_SECRET` as Analytics 2.0, but different scopes)
- Key resources: Properties → Rules → Rule Components (conditions + actions)

**Required credentials (new, not yet in config):**
- Same OAuth2 Client ID/Secret as Analytics 2.0
- Additional IMS scope: `AdobeAnalytics,openid` (check Reactor API docs)
- Tags Property ID (new config field needed)

---

## Implementation Plan

### Step 1 — Research & API exploration

Before writing any code, use a Jupyter notebook to:

1. Authenticate with the Reactor API using existing OAuth2 credentials.
2. Fetch the list of Properties (`GET /properties`).
3. Fetch Rules for a given property (`GET /properties/{id}/rules`).
4. Fetch Rule Components for a rule (`GET /rules/{id}/rule_components`).
5. Inspect Action data to understand how Analytics variables are referenced (field names vary by extension version).

This is a required spike — the data shape is unknown until inspected.

### Step 2 — New service: `app/services/adobe_launch.py`

Create a new service class `AdobeLaunchService`:

- Reuse the existing `OAuth2Auth` from `adobe_auth.py` for token acquisition (may need scope additions).
- Methods:
  - `get_properties()` — list all Tag properties
  - `get_rules(property_id)` — list all rules for a property
  - `get_rule_components(rule_id)` — list conditions + actions for a rule
  - `get_all_rule_actions(property_id)` — flattened list of all actions across all rules (for cross-referencing)

### Step 3 — New config fields

Add to `config.dist.json` and document in README:

```json
{
  "LAUNCH_PROPERTY_ID": "PR...",
  "LAUNCH_ENABLED": true
}
```

The feature should degrade gracefully if `LAUNCH_PROPERTY_ID` is not configured.

### Step 4 — Caching

Add a new cache key `launch_rules` (alongside `processing_rules`, `channel_rules`). TTL can follow the existing 1-hour pattern (or 24 hours once background caching from v2-005 is in place, since Launch rules rarely change).

### Step 5 — Helper: find related Launch rules for a dimension

Add `find_related_launch_rules()` in `main.py`:

1. Load cached Launch rule components.
2. Filter actions where the Analytics extension sets the matching variable.
3. The exact field path depends on findings from Step 1 (e.g. `settings.customSetup.source` or a structured `variables` array).

### Step 6 — Surface on detail pages

Same pattern as v2-001/v2-002:

- Add `related_launch_rules` to detail page template context.
- Add a collapsible "Related Launch Rules" section in `detail.html`, `event_detail.html`, `listvar_detail.html`.
- Show: rule name, rule trigger/condition, action (what the rule does to the variable).
- Handle gracefully when Launch is not configured (hide section entirely).

---

## Files to Create / Change

| File | Change |
|------|--------|
| `app/services/adobe_launch.py` | New service class for Reactor API |
| `app/routes/main.py` | `find_related_launch_rules()` helper; call in detail routes |
| `app/templates/detail.html` | Related Launch Rules section |
| `app/templates/event_detail.html` | Related Launch Rules section |
| `app/templates/listvar_detail.html` | Related Launch Rules section |
| `config.dist.json` | Add `LAUNCH_PROPERTY_ID`, `LAUNCH_ENABLED` |
| `README.md` | Document new config fields |

---

## Risks & Notes

- **Unknown data shape:** The Reactor API response format for rule components varies by extension version. A spike notebook is essential before implementation.
- **Auth scope uncertainty:** May need additional OAuth2 scopes; could require a new API credential if the existing Client ID doesn't have Tags permissions.
- **Rule volume:** Large Launch properties can have hundreds of rules. Fetching and caching all rule components may be slow. Pagination handling required.
- **Not MVP-critical:** If Launch isn't in use or the API is inaccessible, the feature should be fully optional and non-breaking.
- **Suggested order:** Implement after v2-001 and v2-002. Much of the UI pattern will already exist.
