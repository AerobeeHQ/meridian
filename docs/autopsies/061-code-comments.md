# 061 — Code Comments Pass

**Date:** 2026-05-06
**Branch:** `docs/add-code-comments`
**Status:** Complete

---

## Problem

Several core modules contained little or no inline documentation, making the
codebase harder to navigate for developers unfamiliar with the project:

- `app/routes/main.py` had a one-line module docstring that gave no context
  about multi-client routing, the `g`-based service pattern, or error handling.
  The `render_listing()` helper was missing documentation for four of its
  parameters. Lookup tables (`_PRED_LABELS`, `_CONTEXT_LABELS`,
  `_LOGIC_LABELS`) and the `_VAR_RE` regex had no explanatory comments.
- `app/__init__.py` — `_build_client_services()` had a one-line docstring.
  The reasoning behind conditional service creation (API 2.0 vs 1.4, Launch,
  separate OAuth scopes) was not explained.  `create_app()` had no context
  about the multi-client architecture.
- `app/services/cache_warmer.py` — `warm_cache_key()` had a one-line
  docstring that did not explain the fetch_map split between API 1.4 and
  API 2.0, nor why some keys are absent for API 1.4-only clients.
  `CONFIG_CACHE_KEYS` lacked a comment explaining the lazy vs. pre-warmed
  caching strategy.
- `app/services/adobe_launch.py` — `_headers()` had no docstring explaining
  the required JSON:API media type. The complex three-step logic inside
  `search_and_resolve()` (strategy A/B classification, parallel resolution,
  deduplicated output) was not annotated with step headings.

---

## Solution

Added targeted comments and docstrings to the four modules above.  No logic
was changed — only documentation.

### `app/routes/main.py`

- Expanded the module docstring to describe the route pattern, multi-client
  routing mechanism, and error handling approach.
- Documented all parameters of `render_listing()` including the previously
  undocumented `dt_order`, `column_badges`, `preformatted_columns`, and
  `dt_column_widths` arguments.
- Added a two-line comment above `_VAR_RE` explaining the regex pattern and
  why word-boundary anchors are necessary.
- Added a comment block above `_PRED_LABELS` / `_CONTEXT_LABELS` /
  `_LOGIC_LABELS` explaining that these map Adobe API internal `func` keys
  to plain-English display labels.

### `app/__init__.py`

- Rewrote `_build_client_services()` docstring to list each service created,
  when it is created, what credentials it requires, and what error it raises.
- Rewrote `create_app()` docstring to explain the application factory pattern
  and the multi-client architecture.
- Added an inline comment explaining why Launch gets its own `OAuth2Auth`
  instance with broader Reactor scopes.
- Added an inline comment clarifying why each client's cache lives in its own
  subdirectory.

### `app/services/cache_warmer.py`

- Added a multi-line comment above `CONFIG_CACHE_KEYS` explaining the
  distinction between pre-warmed configuration keys (24h TTL) and lazily
  populated detail/trend keys (1h TTL).
- Rewrote `warm_cache_key()` docstring with full Args documentation and an
  explanation of which keys use API 1.4 vs API 2.0.
- Added inline comments labelling the two sections of `fetch_map`.

### `app/services/adobe_launch.py`

- Added a docstring to `_headers()` explaining the required JSON:API Accept
  header and the 406 error that occurs without it.
- Restructured inline comments in `search_and_resolve()` into three clearly
  labelled steps:
  1. Categorise rule_component items by resolution strategy.
  2. Resolve rule names in parallel.
  3. Build the deduplicated results list.
- Explained the purpose of `strategy_a`, `strategy_b`, `component_by_rule`,
  and `component_by_comp` in the step-1 comment block.

---

## Files Changed

| File | Change |
|------|--------|
| `app/routes/main.py` | Expanded module docstring; full `render_listing()` param docs; `_VAR_RE` and label-table comments |
| `app/__init__.py` | Rewrote `_build_client_services()` and `create_app()` docstrings; added inline comments |
| `app/services/cache_warmer.py` | `CONFIG_CACHE_KEYS` comment; rewrote `warm_cache_key()` docstring; inline fetch_map labels |
| `app/services/adobe_launch.py` | `_headers()` docstring; step-labelled comments in `search_and_resolve()` |
| `docs/autopsies/061-code-comments.md` | This document |

---

## Tests

All 131 existing tests pass without modification.  Documentation-only changes
carry no regression risk.
