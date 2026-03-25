# 019 — Rename `table.html` to `listing.html`

**Date:** March 25, 2026
**Status:** Completed
**Branch:** `chore/rename-table-template`

## Summary

Renamed the generic listing template from `table.html` to `listing.html` to better reflect its purpose. Updated all call sites in `app/routes/main.py` (9 references). Also corrected two stale `[ ]` entries in `docs/todo.md` that were accidentally un-ticked when PR #27 was reverted.

## Problem Statement

The template used for every dimension/metric listing page was named `table.html`. This name is ambiguous: the word "table" describes an HTML element, a database table, a lookup table — not a page that lists Adobe Analytics dimensions. Anyone new to the codebase (or returning after a break) has no immediate idea what this template is for.

The todo listed it as:

> Change the data dimensions listing page template name. I think it is `table.html` at the moment, but it would be clearer if it was something else like `listing.html`, or `summary.html`, or `props.html + evars.html + events.html + listVars.html`.

## Decision: `listing.html`

The todo offered several options. The trade-offs:

- **`listing.html`** — one shared template, minimal change, immediately clear intent. ✅ Chosen.
- **`summary.html`** — slightly more ambiguous (could be a stats summary).
- **Per-entity templates** (`props.html`, `evars.html`, etc.) — cleaner long-term but premature while the template body is nearly identical across all entities. Splitting should happen if/when columns diverge significantly (e.g. when eVar allocation/expiration columns are added back).

`listing.html` is the lowest-risk rename that eliminates the confusion without over-engineering the template layer today.

## Changes

### `app/templates/`

- Deleted `table.html`.
- Created `listing.html` with identical content (copy → delete, tracked by git as a rename).

### `app/routes/main.py`

Updated all 9 `render_template('table.html', ...)` calls to `render_template('listing.html', ...)`. Affected routes:

| Route | URL |
|---|---|
| `props` | `/props` |
| `evars` | `/evars` |
| `events` | `/events` |
| `listvars` | `/listvars` |
| `core_dimensions` | `/core` |
| `list_processing_rules` | `/processing-rules` |
| `list_channel_rules` | `/channel-rules` |
| `list_classification_sets` | `/classification-sets` |
| `list_segments` | `/segments` |

### `docs/todo.md`

- Marked the template rename item as done.
- Marked the merchandising eVar expiration bug as done — this was fixed in PR #26 (autopsies 016 and 017) but the checkbox was accidentally reverted to `[ ]` when PR #27 was rolled back.

## Why This Approach

This is a pure rename — no logic changes, no risk to data paths or API calls. Git will track the old and new filenames correctly once the delete + add are staged together (`git mv` semantics apply).

The per-entity template split remains a future option if listing pages develop meaningfully different layouts.

## Testing

1. Run `uv run run.py`.
2. Navigate to `/props`, `/evars`, `/events`, `/listvars`, `/core`, `/processing-rules`, `/channel-rules`, `/classification-sets`, `/segments`.
3. Verify each listing page renders correctly with no template-not-found errors.
4. Confirm `table.html` no longer exists under `app/templates/`.
