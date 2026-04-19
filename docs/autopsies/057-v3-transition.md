# 057 — Version 3 Transition

**Date:** 2026-04-19
**Status:** Complete

---

## Summary

Transitioned Codex from Version 2 (complete) to Version 3 (active development). This involved updating roadmap documents, cleaning up todo.md, and aligning documentation to reflect the project's current state.

---

## Changes Made

### Documentation Updates

| File | Change |
|------|--------|
| `docs/todo.md` | Cleaned up structure; moved completed v2 items to "Dones" section; updated format to be more concise; confirmed no active bugs |
| `docs/version-2-roadmap.md` | Marked as **Complete**; updated Feature Overview table (Themes & Settings marked Done, User OAuth moved to v3); converted "Suggested Implementation Order" to "Implementation Order (Completed)" |
| `docs/version-3-roadmap.md` | Reformatted to match v2 roadmap structure; added Feature Overview table with statuses; added Suggested Implementation Order section; documented Technical Debt carry-over |
| `README.md` | Updated version to v3.0; updated Roadmap section to reference v3; added v3.0 to Version History; updated last modified date |

### Autopsy Review

Reviewed all 56 autopsies for recurring patterns. Key findings:

1. **API 1.4 unreliability** — Multiple autopsies (011, 017, 022, 023, 024) address API 1.4 timeout and fallback issues. This validates the urgency of v3-002 (API 1.4 Deprecation Strategy).

2. **Trend chart data accuracy** — Autopsy 048 was a significant fix where trend charts showed report-suite-wide data instead of dimension-specific data. Each dimension type (eVar, prop, event, listVar) needed a different scoping strategy. This highlights the complexity of the Adobe Analytics API.

3. **Detail page templates** — Autopsy 035 identified that `detail.html`, `event_detail.html`, and `listvar_detail.html` are ~75% structurally identical. This remains technical debt carried into v3.

4. **Classification handling** — Multiple fixes (032, 041) dealt with how classifications (e.g., `evar8.suburb`) should be displayed differently from parent dimensions. Processing rules/channel rules/Launch panels are now hidden for classifications.

### Codebase Review

Scanned `main.py` (2,706 lines), service layer, and templates for potential bugs. No new bugs found. The codebase is clean with no TODO/FIXME/HACK markers.

---

## Recommended v3 Implementation Order

Based on risk assessment and dependencies:

1. **API 1.4 Deprecation Strategy** — Highest risk; Adobe shutdown is August 2026
2. **Unit & Integration Tests** — Foundation for safer development
3. **Report Suite Selection** — Low risk, high UX value
4. **Adobe Launch Property Mapping** — Depends on #3
5. **Self-Hosted Assets** — Low effort, removes external dependencies
6. **User OAuth Login** — Largest architectural change; scaffolding ready
7. **Adobe Spectrum Theme** — Nice-to-have polish
8. **Documentation Improvements** — Ongoing

---

## Files Created/Changed

| File | Action |
|------|--------|
| `docs/todo.md` | Updated |
| `docs/version-2-roadmap.md` | Updated |
| `docs/version-3-roadmap.md` | Updated |
| `README.md` | Updated |
| `docs/autopsies/057-v3-transition.md` | Created |

