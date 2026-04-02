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

### Correct URL pattern (discovered by inspecting live browser URL)

| Entry type | URL |
|------------|-----|
| Rule | `https://experience.adobe.com/#/@{org}/sname:prod/data-collection/tags/companies/{reactor_co_id}/properties/{property_id}/rules/{rule_id}` |
| Data Element | `.../properties/{property_id}/data-elements/{source_id}` |
| Extension | `.../properties/{property_id}/extensions/{source_id}` |

Key findings versus the initial attempt:

| Segment | Initial (wrong) | Correct |
|---------|----------------|---------|
| Shell context | `so:{globalCompanyId}` (Analytics ID) | `sname:prod` (fixed string for production) |
| Company path | absent | `/companies/{reactor_company_id}` |

`{reactor_company_id}` is the `CO...` ID returned by `GET /companies` on the Reactor API — distinct from the Analytics API's `globalCompanyId`.

All required identifiers:
- `{org}` — `EXPERIENCE_CLOUD_ORG` config key (added in autopsy 042)
- `{reactor_company_id}` — from `GET https://reactor.adobe.io/companies`
- `{property_id}` — `LAUNCH_PROPERTY_ID` config key (already in use)
- `{rule_id}` / `{source_id}` — from the Reactor API search results already in each entry

**Link priority in the panel:**

1. **Launchpad** (`launchpad_url + property_id` set) — unchanged for existing users
2. **Adobe Tags** (`adobe_tags_base + property_id` available) — new fallback
3. **Plain text** — when neither is configured

Note: Launchpad uses `property/` (singular) in its URL paths; Adobe Tags uses `properties/` (plural). The macro handles each independently.

---

## Changes

### `app/services/adobe_launch.py`

Added two methods to `AdobeLaunchService`:

**`get_company_id()`** — calls `GET /companies` once and caches the Reactor company ID (`CO...`) on the instance. Returns `None` on failure.

**`get_tags_base_url(org_alias)`** — composes the full base URL using `sname:prod` and the Reactor company ID:

```python
def get_tags_base_url(self, org_alias):
    if not org_alias:
        return None
    company_id = self.get_company_id()
    if not company_id:
        return None
    return (
        f"https://experience.adobe.com/#/@{org_alias}"
        f"/sname:prod/data-collection/tags/companies/{company_id}"
    )
```

### `app/routes/main.py`

In `api_related_launch_rules`, calls `launch_service.get_tags_base_url(org_alias)` (the Launch service already exists at this point in the route). Errors are silently caught so a missing `EXPERIENCE_CLOUD_ORG` never breaks the panel.

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

- One additional API call: `GET /companies` on the Reactor API, made once per process lifetime and cached on the service instance.
- `rel="noopener noreferrer"` added to all launch links (was missing `noreferrer` previously).
- URL path difference: Launchpad uses `/property/{id}/...` (singular); Adobe Tags uses `/properties/{id}/...` (plural).
