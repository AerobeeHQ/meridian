# 033 — Processing Rules Condition Formatting

**Date:** 2026-03-26
**Branch:** `fix/processing-rules-formatting`
**Status:** Complete

---

## Problem

The Processing Rules listing page showed all conditions for a rule as a single long line — e.g.:

```
if user_server notequals any of (...) AND if contextdata.a.appid notstartswith any of (...) AND if evar22 notequals any of (...)
```

Rules with multiple conditions (3–5 are common) were nearly unreadable in the table. The same raw string was also displayed in `<pre>` blocks on the "Related Processing Rules" card on dimension detail pages.

---

## Changes

### `app/routes/main.py`

**Added `format_conditions(text)`** — a small helper that splits on ` AND ` and rejoins with `\nAND `, putting each condition clause on its own line:

```python
def format_conditions(text: str) -> str:
    if not text:
        return text
    return text.replace(' AND ', '\nAND ')
```

**Processing rules listing route** — applies `format_conditions` to the `Conditions` column after `transform_data`, then passes it as `preformatted_columns` instead of `monospace_columns`:

```python
for row in data:
    if row.get('Conditions'):
        row['Conditions'] = format_conditions(row['Conditions'])

return render_listing(...,
    monospace_columns=['Actions'],
    preformatted_columns=['Conditions'],
    ...)
```

**Related rules fragment route** — creates new rule dicts with formatted `rules` field before passing to the template, so the `<pre>` blocks on detail pages also benefit:

```python
formatted_rules = [
    {**rule, 'rules': format_conditions(rule.get('rules', ''))}
    for rule in related_rules
]
```

**`render_listing()`** — added `preformatted_columns=None` parameter, forwarded to the template as a list.

### `app/templates/listing.html`

Added a `preformatted_columns` rendering branch — renders content in a `<pre class="monospace small mb-0">` block, which preserves the newlines inserted by `format_conditions`. The `<td>` gets `vertical-align: top` to prevent awkward cell centring.

---

## Result

Each condition in a multi-condition rule now appears on its own line:

```
if user_server notequals any of (...)
AND if contextdata.a.appid notstartswith any of (...)
AND if evar22 notequals any of (...)
```

This applies to both the Processing Rules listing page and the Related Processing Rules card on dimension detail pages.

---

## Notes

- Actions are left in `monospace_columns` (single `<code>` element) — each row already has one action.
- The cached raw data is never modified; formatting is applied at display time.
