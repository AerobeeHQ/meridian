# 030 — Fix: Processing Rules Monospace Font Size and Colour

**Date:** 2026-03-26
**Branch:** `fix/processing-rules-monospace`
**Status:** Complete

---

## Problem

Monospace text on the Processing Rules and Channel Rules listing pages had two visual issues:

1. **Too small** — `.monospace` used a hardcoded `font-size: 12px`, which is smaller than the surrounding table text and doesn't scale with any parent font-size changes.
2. **Plain black** — Bootstrap 5 styles `<code>` elements with a pink/red colour (`#d63384`) and a relative `0.875em` size. Other pages (e.g. Segment Details) already use `<code>` and look consistent with Bootstrap's design language. The processing rules listing used a plain `<td class="monospace">` which produced black Courier New instead.

---

## Changes

### `app/templates/base.html`
Changed `.monospace` font-size from a hardcoded pixel value to a relative unit:

```css
/* Before */
.monospace { font-family: 'Courier New', monospace; font-size: 12px; }

/* After */
.monospace { font-family: 'Courier New', monospace; font-size: 0.875em; }
```

`0.875em` is Bootstrap's standard code font size (`$code-font-size`). Using a relative unit means the size scales correctly with its parent context, matching surrounding text proportionally.

### `app/templates/listing.html`
Added a dedicated `elif` branch in the table cell renderer so monospace-column content is wrapped in `<code>` tags:

```jinja2
{% elif col in monospace_columns %}
    <code>{{ row[col] if row[col] is not none else '' }}</code>
```

The `<code>` element inherits Bootstrap's native styling automatically — pink colour and relative monospace sizing — with no additional CSS needed. This makes the Actions and Conditions columns on the Processing Rules listing, and equivalent columns on Channel Rules, visually consistent with `<code>` usage elsewhere in the app (e.g. Segment Detail, eVar/Prop detail pages).

---

## Scope

- Affects: `/processing-rules` and `/channel-rules` listing pages (the two places `monospace_columns` is populated in `render_listing()`)
- The `.monospace` class also applies to `<pre>` blocks in `_macros.html` (Related Processing Rules section on detail pages). Changing `12px` → `0.875em` there improves those blocks too — they now size relative to the card body instead of being locked to 12px.
- No API changes. No route changes. Template and CSS only.
