# 045 — README Documentation Improvements

**Date:** 2026-04-02
**Branch:** `fix/readme-doc-improvements`
**Status:** Complete

---

## Problem

Two open items in `todo.md` asked for README additions:

1. **Known Issues** — a section linking users to the active bug list so they are aware of current limitations before filing duplicate issues.
2. **Version History** — a structured changelog so users can see what changed between v1.0 and v2.0.

A third item — "use pill style in the Components panel" — was also open in `todo.md`, but the code already used `badge bg-light text-dark border` pill badges (implemented as part of [autopsy 028](028-components-panel.md)). The checkbox had never been ticked.

---

## Solution

### 1. Known Issues section — `README.md`

Added a concise table of the two active bugs from `todo.md`:

- Trendline chart shows peaks/valleys for dimensions with no recent data
- API Debug page blocks all POST requests, including read-only ones

The section links to `docs/todo.md` for the full list.

### 2. Version History section — `README.md`

Added two version tables covering the full project history:

- **v1.0 (December 2025)** — initial Flask conversion from RShiny: eVars, Props, Events, ListVars, Processing Rules, Marketing Channels, CSV export, file-based caching.
- **v2.0 (March–April 2026)** — all new features: Segments, Calculated Metrics, Launch integration, Background Pre-Caching, API/Reactor Debug, Dimension Notes, Data Feed columns, and more.

### 3. Components pill-style checkbox — `docs/todo.md`

Marked the open "Components pill style" item as done. The `components_section` macro in `_macros.html` already uses `badge bg-light text-dark border me-1 mb-1 text-decoration-none` for both segment and metric links — identical to the pill style on segment/metric detail pages. This was implemented as part of autopsy 028 but never checked off.

---

## Changes

| File | Change |
|------|--------|
| `README.md` | Added **Known Issues** table (2 active bugs); added **Version History** tables for v1.0 and v2.0 |
| `docs/todo.md` | Marked Components pill-style item as done with explanation |

---

## Notes

- The "Planned for v2.0" section in the README already covers the roadmap; Version History complements it by documenting what *has* shipped rather than what is planned.
- Known Issues will need updating when bugs are resolved or new ones are confirmed.
