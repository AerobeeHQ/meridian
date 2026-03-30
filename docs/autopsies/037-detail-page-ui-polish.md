# 037 — Fix: Detail Page UI Polish (Data Feed Column + Components Pills)

**Date:** 2026-03-30
**Branch:** `fix/detail-page-ui-polish`
**Status:** Complete

---

## Problems

Two small UI issues on dimension detail pages (props, eVars):

1. **Data Feed Column showed classified suffix** — visiting `/evars/evar8.suburb` displayed `post_evar8.suburb` as the Data Feed Column. Classifications don't have their own data feed columns; the column is always the parent dimension (e.g. `post_evar8`). The same bug also affected the Instance Event token calculation, where `evar8.suburb` would fail the `| int` filter.

2. **Components panel used plain hyperlinks** — the Segments and Calculated Metrics listed in the Components accordion used `<ul><li><a>` markup, while the Segment Detail and Calculated Metric Detail pages already display referenced variables as styled pill badges (`badge bg-light text-dark border`). The inconsistency made the Components panel look unfinished.

---

## Changes

### `app/templates/detail.html`

Split `dimension_id` on `.` before using it, so classifications resolve to their parent:

```jinja2
{# Before #}
<td><code>post_{{ dimension_id }}</code></td>
{% set evar_num = dimension_id | replace('evar', '') | int %}

{# After #}
<td><code>post_{{ dimension_id.split('.')[0] }}</code></td>
{% set evar_num = dimension_id.split('.')[0] | replace('evar', '') | int %}
```

For a non-classified dimension like `evar8`, `split('.')[0]` returns `evar8` unchanged. For `evar8.suburb`, it returns `evar8`.

### `app/templates/_macros.html`

Replaced the `<ul><li><a>` list with inline pill badges in both the Segments and Calculated Metrics accordion bodies inside `components_section`:

```jinja2
{# Before #}
<ul class="list-unstyled mb-0">
    {% for seg in components.segments %}
    <li class="mb-1">
        <a href="/segments/{{ seg.id }}">{{ seg.name }}</a>
    </li>
    {% endfor %}
</ul>

{# After #}
{% for seg in components.segments %}
<a href="/segments/{{ seg.id }}"
   class="badge bg-light text-dark border me-1 mb-1 text-decoration-none">{{ seg.name }}</a>
{% endfor %}
```

The same pattern was applied to the Calculated Metrics section. The pill classes (`badge bg-light text-dark border me-1 mb-1 text-decoration-none`) match the existing style on `segment_detail.html` and `calc_metric_detail.html`.

---

## Scope

- **Affects:** Prop and eVar detail pages (Data Feed Column, Instance Event), and the Components panel on all dimension detail pages (props, eVars, events, listvars).
- No API changes. No route changes. Template-only.
- Sourced from `docs/todo.md` — the Data Feed Column classified bug and the Components pill style todo item.
