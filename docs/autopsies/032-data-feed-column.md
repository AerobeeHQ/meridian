# 032 — Data Feed Column Name on Dimension Detail Pages

**Date:** 2026-03-26
**Branch:** `feature/data-feed-column`
**Status:** Complete

---

## Problem

The Prop, eVar, and ListVar detail pages showed variable configuration (allocation, expiration, pathing, etc.) but did not show the corresponding Adobe Analytics Data Feed column name. Analysts who cross-reference raw data feed exports needed to look up these names externally.

## Solution

The official [Adobe Analytics Data Feed documentation](https://experienceleague.adobe.com/en/docs/analytics/export/analytics-data-feed/data-feed-contents/datafeeds-reference) lists the column names for each variable type, and the [Events.tsv](../event.tsv) file was used as the basis for the mapping.

---

## Mapping

| Variable | Data Feed Column |
|----------|-----------------|
| prop1 … prop75 | `post_prop1` … `post_prop75` |
| eVar1 … eVar250 | `post_evar1` … `post_evar250` |
| List Var 1 … 3 | `post_list1` … `post_list3` |

The mapping is deterministic (no API call needed) — the column name is `post_` + the variable ID for props and eVars, and `post_list` + the number for ListVars.

---

## Changes

### `app/templates/detail.html`

Added a **Data Feed Column** row to the Dimension Configuration table, immediately before the Description row:

```jinja2
<tr>
    <th>Data Feed Column</th>
    <td><code>post_{{ dimension_id }}</code></td>
</tr>
```

`dimension_id` in this template is already the short form (`prop1`, `evar5`), so `post_prop1` / `post_evar5` renders correctly for both props and eVars with no branching logic.

### `app/templates/listvar_detail.html`

Added a **Data Feed Column** row to the ListVar Configuration table:

```jinja2
<tr>
    <th>Data Feed Column</th>
    <td><code>post_list{{ listvar_num }}</code></td>
</tr>
```

---

## Notes

- No route changes. No API calls. Template-only change.
- The `<code>` element uses Bootstrap's native pink monospace styling, consistent with other technical identifiers in the app.
