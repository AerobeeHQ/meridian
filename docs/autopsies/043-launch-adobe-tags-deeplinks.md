# 043 — Adobe Tags Deep-links for Launch Rules

**Date:** 2026-04-02
**Branch:** `feature/launch-adobe-tags-deeplinks`
**Status:** Complete

---

## Problem

The "Adobe Launch" panel on dimension detail pages listed matching rules, data elements, and extensions as plain text when the optional `LAUNCHPAD_URL` was not configured. The todo asked:

> Hyperlink the Adobe Launch rule into Adobe Tags website.

Analysts needed to leave Codex and manually navigate to the correct rule in the Adobe Experience Platform Tags UI.

---

## Solution

Add the native Adobe Experience Platform Tags UI as a link destination — either as a fallback when Launchpad is not configured, or as the primary link if Launchpad is absent.

The Tags UI URL pattern is:

| Entry type | URL |
|------------|-----|
| Rule | `https://experience.adobe.com/#/@{org}/so:{company}/data-collection/tags/properties/{property_id}/rules/{rule_id}` |
| Data Element | `.../properties/{property_id}/data-elements/{source_id}` |
| Extension | `.../properties/{property_id}/extensions/{source_id}` |

All three identifiers are already available:
- `{org}` — `EXPERIENCE_CLOUD_ORG` config key (added in autopsy 042)
- `{company}` — `globalCompanyId` from the Analytics 2.0 discovery endpoint (already cached in memory)
- `{property_id}` — `LAUNCH_PROPERTY_ID` config key (already in use)
- `{rule_id}` / `{source_id}` — from the Reactor API search results

**Link priority in the panel:**

1. **Launchpad** (`launchpad_url + property_id` set) — unchanged for existing users
2. **Adobe Tags** (`adobe_tags_base + property_id` available) — new fallback
3. **Plain text** — when neither is configured

Note: Launchpad uses `property/` (singular) in its URL paths; Adobe Tags uses `properties/` (plural). The macro handles each independently.

---

## Changes

### `app/services/adobe_analytics_v2.py`

Added `get_tags_base_url(org_alias)` — returns the root Tags UI URL up to (but not including) the property path. Same pattern as `get_experience_cloud_url`; returns `None` when `org_alias` or `globalCompanyId` is unavailable.

```python
def get_tags_base_url(self, org_alias=None):
    if not org_alias:
        return None
    global_company_id = self._get_global_company_id()
    return (
        f"https://experience.adobe.com/#/@{org_alias}"
        f"/so:{global_company_id}/data-collection/tags"
    )
```

### `app/routes/main.py`

In `api_related_launch_rules`, after the search is complete, calls `v2_svc.get_tags_base_url(org_alias)` and passes the result as `adobe_tags_base` to the fragment template. Errors are silently caught so a misconfigured `EXPERIENCE_CLOUD_ORG` never breaks the panel.

### `app/templates/_fragment_related_launch_rules.html`

Passes the new `adobe_tags_base` variable through to the macro.

### `app/templates/_macros.html`

Updated `related_launch_rules_section` signature to accept `adobe_tags_base=''`. Replaced the three separate `launchpad_url` link blocks with a single `link_base` variable resolved once per entry:

```jinja2
{% if launchpad_url and property_id %}
    {% set link_base = launchpad_url ~ '/property/' ~ property_id %}
{% elif adobe_tags_base and property_id %}
    {% set link_base = adobe_tags_base ~ '/properties/' ~ property_id %}
{% else %}
    {% set link_base = '' %}
{% endif %}
```

Each entry type (`rule`, `data_element`, `extension`) then uses `link_base` to build its href, reducing duplication.

---

## Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| `EXPERIENCE_CLOUD_ORG` not set | `adobe_tags_base` is `None`; no Tags link shown |
| `LAUNCH_PROPERTY_ID` not set | `link_base` is empty; plain text shown |
| `launchpad_url` set | Launchpad links take priority; Tags URL not used |
| Tags URL service call fails | Exception caught in route; `adobe_tags_base = None` |

---

## Notes

- No new API calls. `globalCompanyId` is already cached from startup.
- `rel="noopener noreferrer"` added to all launch links (was missing `noreferrer` previously).
- URL path difference: Launchpad uses `/property/{id}/...` (singular); Adobe Tags uses `/properties/{id}/...` (plural).
