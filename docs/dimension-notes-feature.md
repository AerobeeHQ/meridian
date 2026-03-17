# Dimension Notes Feature Plan

**Created:** March 14, 2026  
**Updated:** March 17, 2026

## Overview

This feature adds the ability to store user-provided notes for each data dimension (props, evars, events, listvars). Given the project's MVP velocity philosophy, low expected concurrency (<10 users), and small data size (a few sentences), a **JSON file-based approach** is recommended. This mirrors the existing cache service pattern, keeps dependencies minimal, and avoids database setup complexity.

## Steps

### 1. Create new `NotesService`

**File:** `app/services/notes.py`

Store notes as JSON files in a `notes/` directory, keyed by `{rsid}_{dimension_type}_{dimension_id}`. Include `get()`, `set()`, and `delete()` methods.

### 2. Add API routes

**File:** `app/routes/main.py`

Add `GET /api/notes/<dimension_type>/<dimension_id>` and `POST /api/notes/<dimension_type>/<dimension_id>` endpoints to fetch and save notes.

### 3. Update detail templates

Add a "Notes" card with a simple textarea (or basic markdown editor) and save button to:
- `app/templates/detail.html`
- `app/templates/event_detail.html`
- `app/templates/listvar_detail.html`

### 4. Add JavaScript handler

Implement fetch-based AJAX for note saving directly in the templates (or a shared `<script>` block in `app/templates/base.html`).

### 5. Create `notes/` directory setup

Add directory creation to app initialization and `.gitignore` entry for `notes/`.

## Further Considerations

### 1. Markdown support?

Could use a lightweight JS library like [SimpleMDE](https://simplemde.com/) for rich editing, or keep plain textarea for MVP and add later.

**Recommendation:** Start with plain textarea.

### 2. Note metadata?

Store author + timestamp alongside note content? Useful for auditing but adds complexity.

**Recommendation:** Add `updated_at` timestamp only.

### 3. Note history/versioning?

Keep previous versions when a note is updated?

**Recommendation:** Not for MVP — overwrite is simpler.

## Storage Rationale

| Option | Pros | Cons |
|--------|------|------|
| **JSON files (chosen)** | Matches existing cache pattern, zero dependencies, easy backup, human-readable | No concurrent write safety (acceptable for <10 users) |
| SQLite | ACID compliance, query capability | Adds dependency, overkill for simple key-value notes |
| Parse/BaaS | Managed service, real-time sync | External dependency, cost, network latency |
| Database (Postgres/MySQL) | Robust, scalable | Significant setup overhead, not MVP-friendly |

## Search Compatibility

**Context:** A keyword search feature is planned to help users find dimensions/metrics.

**Decision:** JSON storage remains appropriate because:

1. **Primary search scope** — Search will target Adobe Analytics config data (eVars, props, events names/IDs/descriptions), which is already cached in `cache/{rsid}.json`
2. **Notes search deferred** — If users need to search inside notes later, an in-memory index can be built on app startup
3. **Scale is tiny** — Even worst-case (500 notes × 1KB each = 500KB), loading all files is fast

**Future upgrade path:** If notes search becomes essential, options include:
- Build in-memory index on startup (load all `notes/*.json` into a dict)
- Migrate to SQLite for SQL `LIKE` queries

## Implementation Status

| Step | Status | Notes |
|------|--------|-------|
| 1. Create `NotesService` | ✅ Complete | `app/services/notes.py` |
| 2. Add API routes | ✅ Complete | GET/POST/DELETE in `main.py` |
| 3. Update detail templates | ✅ Complete | UI added to all 3 templates |
| 4. Add JavaScript handler | ✅ Complete | `notes_js` macro in `_macros.html` |
| 5. Create `notes/` directory | ✅ Complete | Auto-created on first save, added to `.gitignore` |

## Custom Notes (v2 - Structured Fields)

**Status:** ✅ Implemented (March 17, 2026)

Expanded the simple freeform notes to a structured form with multiple fields:

| Field | Type | Max Length | Description |
|-------|------|------------|-------------|
| Plain English Description | textarea (3 rows) | 1000 chars | Business user-friendly description |
| Technical Definition | textarea (3 rows) | 1000 chars | Technical implementation details |
| Expiry Notes | textarea (2 rows) | 500 chars | Auto-generated from API, user can override |
| Platform Availability | dropdown | - | Web Only, App Only, Both Web and App |
| Platform Notes | textarea (2 rows) | 500 chars | Platform-specific implementation notes |
| Web Equivalent | dropdown | - | Link to corresponding web dimension |
| App Equivalent | dropdown | - | Link to corresponding app dimension |
| Use Cases | textarea (3 rows) | 1000 chars | Common analysis scenarios |
| Typical Questions | textarea (3 rows) | 1000 chars | Business questions this helps answer |
| Journey Squad Owner | tag chips | - | Multi-select: Shop, Inspire, Checkout, etc. |
| Last Verified | date input | - | When documentation was last verified |

### JSON Storage Schema

```json
{
  "plain_description": "...",
  "technical_definition": "...",
  "expiry_notes": "...",
  "platform_availability": "web_only|app_only|both|",
  "platform_notes": "...",
  "web_equivalent": "evar5|none|",
  "app_equivalent": "evar10|none|",
  "use_cases": "...",
  "typical_questions": "...",
  "squad_owners": ["Shop", "Checkout"],
  "last_verified": "2026-03-17",
  "updated_at": "2026-03-17T10:30:00+00:00"
}
```

### Files Modified

- `app/services/notes.py` — Updated to handle structured data, added `SQUAD_OPTIONS`, `PLATFORM_OPTIONS`, `get_empty_note()`, `generate_expiry_notes()`
- `app/routes/main.py` — Updated API routes for structured data, added `/api/notes/options/<dimension_type>` endpoint
- `app/templates/_macros.html` — Added `notes_form` macro (HTML) and `notes_form_js` macro (JavaScript)
- `app/templates/detail.html`, `event_detail.html`, `listvar_detail.html` — Updated to use new structured form

## UX Improvements

### Option A: Conditional Single Dropdown (March 17, 2026)

Replaced redundant Web/App Equivalent dropdowns with a single conditional dropdown:
- **"Not Set"** → No equivalent dropdown shown
- **"Web Only"** → Shows "App Equivalent" dropdown
- **"App Only"** → Shows "Web Equivalent" dropdown
- **"Both Web and App"** → Shows message "No equivalent needed"

### Keyword Filter for Equivalent Dropdown (March 17, 2026)

Added a keyword filter input above the platform equivalent dropdown to help users quickly find options in long lists (especially useful for Success Events with hundreds of values):
- Text input filters options as you type
- Matches against both dimension ID (e.g., "event123") and name (e.g., "Purchase Complete")
- Filter is cleared when platform selection changes
- Filter input does not trigger auto-save