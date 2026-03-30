# 038 — Feature: Segment Definition Human-Readable Breakdown

**Date:** 2026-03-30
**Branch:** `feature/segment-definition-breakdown`
**Status:** Complete
**Source:** `docs/todo.md` — Suggested Improvement Item 6

---

## Problem

The Segment Detail page displayed the segment definition as raw JSON in a `<pre>` block. For simple segments this is workable, but complex multi-container segments with AND/OR logic, sequences, and nested containers are very difficult to interpret from raw JSON alone.

---

## Solution

Added a recursive definition parser that walks the Adobe Analytics 2.0 segment definition tree and produces a flat list of display rows, each with a depth (for indentation), text label, and kind (for styling). The template renders these as an indented, colour-coded breakdown.

---

## Architecture

### Parser: `_walk_segment_definition()` in `app/routes/main.py`

A recursive walker that handles every node type in the segment definition schema:

| Node type | `func` values | Output |
|-----------|--------------|--------|
| **Top-level** | `segment` | Descends into `container` |
| **Container** | `container` | Badge showing scope (`Hit`, `Visit`, `Visitor`) |
| **Boolean logic** | `and`, `or`, `without` | Operator label between child nodes |
| **Sequences** | `sequence`, `sequence-prefix`, `sequence-suffix`, `sequence-and`, `sequence-or` | `THEN` / `AND (unordered)` / `OR (unordered)` between stream items |
| **Time restrictions** | `time-restriction`, `container-restriction`, `dimension-restriction` | Italic label (e.g. "within 1 month") |
| **Leaf predicates** | `streq`, `contains`, `exists`, `gt`, `eq-any-of`, etc. | Code-formatted rule (e.g. `page equals "Home"`) |

Supporting helpers:

- `_attr_name()` — extracts a readable name from `attr`, `event`, or `total` value nodes
- `_pred_value()` — formats comparison values (`str`, `num`, `list`, `glob`) with truncation for long lists
- `_PRED_LABELS` — maps all 30+ API func names to user-facing operator labels
- `_CONTEXT_LABELS` / `_LOGIC_LABELS` — scope and boolean operator display names

### Template: `segment_detail.html`

The right column now has two cards:

1. **Segment Definition** — the human-readable breakdown, rendered as indented rows with depth-based padding (`padding-left: depth * 20px`). Each row kind gets distinct styling:
   - `container` → Bootstrap badge (`bg-secondary`)
   - `operator` → Bold blue text
   - `time` → Italic muted text
   - `rule` → Monospace `<code>` element

2. **Raw JSON Definition** — the original `<pre>` block, now inside a collapsible accordion (matching the pattern used on the Calculated Metrics detail page). Collapsed by default.

### Route: `segment_detail()`

Two new lines: parse the definition and pass `breakdown` to the template. No additional API calls — the definition is already present in the segment response.

---

## Scope

- **Affects:** `/segments/<segment_id>` detail page only.
- **New code:** ~120 lines of parser logic, ~30 lines of template markup.
- **No new dependencies.** No API changes. No new routes.
- The parser gracefully handles unknown `func` values by falling through to the leaf predicate renderer, so future Adobe API additions won't break the page — they'll just show the raw func name as the operator label.
