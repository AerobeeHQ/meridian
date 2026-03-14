# Dimension Notes Feature Plan

**Created:** March 14, 2026

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
