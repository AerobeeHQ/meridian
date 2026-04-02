# 042 — Experience Cloud Deep-Links for Segment & Calculated Metric IDs

**Date:** 2026-04-02
**Branch:** `feature/segment-metric-experience-cloud-links`
**Status:** Complete

---

## Problem

The Segment detail page displayed the segment ID as plain `<code>` text, and the Calculated Metric detail page did the same for the metric ID. To open the item in the Adobe Analytics workspace editor an analyst had to manually construct the URL — a friction point when cross-referencing live data against Codex.

The todo asked for:

> Hyperlink the segmentId and metricId shown on their respective detail pages to the Adobe Analytics equivalent. For example, segmentId `s200001582_5df07b97e0a67a0e926c94e1` would link to `https://experience.adobe.com/#/@originenergy/so:origin0/analytics/spa/#/components/segments/edit/s200001582_5df07b97e0a67a0e926c94e1`

---

## Root Cause

The URL requires two company identifiers:

| URL part | Meaning | Source |
|----------|---------|--------|
| `@originenergy` | Company alias (IMS org "short name") | **Not in the Analytics API** — must be configured manually |
| `so:origin0` | Global company ID | `globalCompanyId` in the Analytics API 2.0 discovery response (already in use) |

`globalCompanyId` (`origin0`) is already extracted from `/discovery/me` at startup. The `@originenergy` alias is an IMS org alias managed in the Adobe Admin Console — the discovery endpoint does not return it. Initial implementation attempted to read a `login` field from the discovery response; inspection of the actual payload showed that field is absent:

```json
{
  "imsOrgs": [{
    "imsOrgId": "<ORG_HEX_ID>@AdobeOrg",
    "companies": [{
      "globalCompanyId": "origin0",
      "companyName": "Origin",
      "apiRateLimitPolicy": "aa_api_tier10_tp",
      "dpc": "sin"
    }]
  }]
}
```

The solution is a new optional config key `EXPERIENCE_CLOUD_ORG`.

---

## Solution

### `config.dist.json` + `app/__init__.py`

Added optional `EXPERIENCE_CLOUD_ORG` config key — the company alias after `@` in Experience Cloud URLs. Example: `"originenergy"` for a URL that starts `https://experience.adobe.com/#/@originenergy/...`.

Loaded in `create_app()` as `app.config['EXPERIENCE_CLOUD_ORG']`. Empty string or absent key disables the link silently.

### `app/services/adobe_analytics_v2.py`

Added `get_experience_cloud_url(component_type, component_id, org_alias)` — composes the full deep-link from the caller-supplied `org_alias` and the already-cached `globalCompanyId`. Returns `None` when either is missing.

```python
def get_experience_cloud_url(self, component_type, component_id, org_alias=None):
    if not org_alias:
        return None
    global_company_id = self._get_global_company_id()
    if not global_company_id:
        return None
    base = f"https://experience.adobe.com/#/@{org_alias}/so:{global_company_id}/analytics/spa"
    return f"{base}/#/components/{component_type}/edit/{component_id}"
```

No extra API calls — `globalCompanyId` is already fetched at startup.

### `app/routes/main.py`

In both `segment_detail` and `calculated_metric_detail`, the route reads `EXPERIENCE_CLOUD_ORG` from the app config and passes it to `get_experience_cloud_url(...)`. Errors are caught so a missing or wrong config value never breaks the page.

Component types:
- Segments → `"segments"`
- Calculated Metrics → `"calculatedMetrics"`

### `app/templates/segment_detail.html`

The **Segment ID** row now renders an external link icon (`↗`) next to the `<code>` ID when `experience_cloud_url` is available:

```jinja2
<td>
    <code>{{ segment_id }}</code>
    {% if experience_cloud_url %}
    <a href="{{ experience_cloud_url }}" target="_blank" rel="noopener noreferrer"
       title="Open in Adobe Analytics" class="ms-1 text-muted" style="font-size:12px;">&#8599;</a>
    {% endif %}
</td>
```

### `app/templates/calc_metric_detail.html`

Identical treatment for the **Metric ID** row.

---

## Failure Modes

| Condition | Behaviour |
|-----------|-----------|
| `login` field absent from discovery response | `get_company_login()` returns `None`; link not shown |
| Discovery endpoint unavailable | Exception caught in route; `experience_cloud_url = None`; link not shown |
| API 1.4 mode | Guard skips the call entirely; link not shown |

---

## Notes

- No new API requests are introduced. The discovery endpoint call is already made at startup and the result is kept in memory.
- The link opens in a new tab (`target="_blank"`) and includes `rel="noopener noreferrer"` for security.
- The `↗` arrow icon (`&#8599;`) is a standard Unicode character requiring no additional assets.
