# 020 — Processing Rules on Detail Pages (v2-001)

**Date:** March 25, 2026
**Status:** Completed
**Branch:** `feature/processing-rules-on-detail-pages`
**Roadmap item:** v2-001

## Summary

Added a "Related Processing Rules" section to the detail pages for eVars, Props, Events, and ListVars. When processing rules are already cached (warmed by the `/processing-rules` route), each detail page now cross-references that cache and surfaces any rules that mention the current dimension — without making any additional API calls.

## Problem Statement

Analysts viewing a dimension's detail page could see what the variable is (name, type, expiration, etc.) but had no way to know *how* it gets populated. Processing rules are the most common mechanism for populating variables at collection time, and that data was already fetched and cached by the app — it just wasn't surfaced on detail pages.

## Approach

The plan in `docs/plans/v2-001-processing-rules-integration.md` called for:

1. A helper function to cross-reference cached rules against a dimension ID.
2. Loading the cache in each detail route and passing matching rules to the template.
3. A collapsible UI section showing conditions, actions, and notes per matching rule.

No new API calls are introduced. The processing rules cache is populated when a user visits `/processing-rules` (or when the background pre-cacher runs). If the cache is cold, `related_rules` is simply an empty list and the section shows the "no rules" message — a graceful zero state.

## Matching Logic

`find_related_processing_rules()` in `app/routes/main.py` uses Python `re` with word-boundary anchors and `re.IGNORECASE`:

```python
pattern = re.compile(
    r'\b(' + '|'.join(re.escape(t) for t in safe_terms) + r')\b',
    re.IGNORECASE,
)
```

This prevents false positives like `eVar1` matching `eVar10` or `eVar100`. The pattern is matched against each rule's `rules` (conditions) string and `actions` string.

**Term selection by dimension type:**

| Type | Search term(s) |
|---|---|
| Prop | `prop{N}` (e.g. `prop3`) |
| eVar | `evar{N}` (e.g. `evar5`) |
| Event | `event{N}` (e.g. `event2`) |
| ListVar | `list{N}` **and** `listvar{N}` (e.g. `list1`, `listvar1`) |

ListVars use two terms because Adobe's internal processing rule syntax uses the shorter `list{N}` form, while the API 2.0 dimension ID uses `listvar{N}`.

## Files Changed

| File | Change |
|---|---|
| `app/routes/main.py` | Added `import re` at module level; added `find_related_processing_rules()` helper; updated `prop_detail`, `evar_detail`, `event_detail`, `listvar_detail` routes to load and pass `related_rules`; removed inline `import re` from `listvar_detail` |
| `app/templates/_macros.html` | Added `related_processing_rules_section(related_rules)` macro |
| `app/templates/detail.html` | Imports and calls the macro (props and eVars share this template) |
| `app/templates/event_detail.html` | Imports and calls the macro |
| `app/templates/listvar_detail.html` | Imports and calls the macro |
| `docs/todo.md` | Marked v2-001 processing rules integration item as done |

## UI Details

The section renders as a Bootstrap 5 accordion — each matching rule is a collapsible item showing:

- **Conditions** — the rule's condition text (pre-formatted, monospace)
- **Actions** — the rule's action text, including any ELSE branch (pre-formatted, monospace)
- **Notes** — the rule's comment field, if set

Rules can be expanded independently (no `data-bs-parent` exclusivity). When no rules match, a muted "No processing rules reference this dimension" message is shown. The section always renders so the analyst knows the lookup ran, not just that rules were skipped.

## Limitations

- **Cache dependency:** If the processing rules cache is cold (never visited `/processing-rules`), `related_rules` is empty. Analysts should warm the cache first, or wait for background pre-caching.
- **Best-effort matching:** Rule text is human-authored and may use non-standard variable references. The word-boundary regex catches common patterns; unusual references (e.g. internal Adobe variable codes like `v5`, `c3`) are not currently matched.
- **No new API calls:** This is intentional. The feature deliberately avoids 1.4 API calls on page load to keep detail pages fast. Full resolution of cold-cache scenarios is left to the background pre-cacher (v2-005, already done).

## Testing

1. Visit `/processing-rules` to warm the cache.
2. Navigate to any Prop, eVar, Event, or ListVar detail page that is referenced by at least one processing rule.
3. Verify the "Related Processing Rules" card appears with correct rules collapsed by default.
4. Expand a rule to confirm conditions and actions display correctly.
5. Navigate to a dimension with no matching rules — verify the "No processing rules reference this dimension" state.
