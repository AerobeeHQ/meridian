# 047 — Tags CRUD (rename "Journey Squad Owner" + user-managed tag library)

**Date:** 2026-04-03
**Branch:** `feature/tags-crud`
**Status:** Complete

---

## Problem

The Documentation Notes form on all dimension detail pages had a "Journey Squad Owner" field that rendered a fixed set of squad chips (`Shop`, `Inspire`, `Checkout`, …) hardcoded in two places: the Jinja2 template and `notes.py::SQUAD_OPTIONS`. Users had no way to add, rename, or remove options without editing the source code.

The open todo asked to:
1. Rename the field from "Journey Squad Owner" to **"Tags"**
2. Allow users to **CRUD the available tag options** at runtime

---

## Solution

### 1. Tag library in `notes.py`

Added a dedicated section to `notes.py` that stores the tag library in `notes/_tags.json`:

| Function | Description |
|----------|-------------|
| `get_tags() -> list[str]` | Return the current tag list. Falls back to `SQUAD_OPTIONS` if the file doesn't exist (no migration required). |
| `add_tag(name: str) -> list[str]` | Append a new tag. Raises `ValueError` for empty names or duplicates. |
| `delete_tag(name: str) -> list[str]` | Remove a tag. Raises `ValueError` if not found. |

The file is app-global (`notes/_tags.json`, not per-RSID). The internal `squad_owners` key in existing note JSON files is unchanged — backward compatible.

### 2. Three new API routes in `main.py`

Registered under `/api/tags/` to avoid conflicting with the existing `/api/notes/<type>/<id>` routes:

| Method | Path | Action |
|--------|------|--------|
| `GET` | `/api/tags` | Returns `["Shop", "Inspire", …]` |
| `POST` | `/api/tags` | Adds a tag. Body: `{"name": "NewTag"}`. Returns `{"tags": [...]}`. Responds 409 on duplicate. |
| `DELETE` | `/api/tags/<tag_name>` | Removes a tag. Returns `{"tags": [...]}`. Responds 404 if missing. |

### 3. Template changes in `_macros.html`

**`notes_form` macro (HTML):**
- Renamed section label from "Journey Squad Owner" to **"Tags"**
- Removed the hardcoded Jinja2 `{% for squad in [...] %}` loop
- Added an empty `<div class="squad-chips">` (populated from API)
- Added a collapsible add-tag row (hidden until "Manage" clicked):
  - Text input + **Add** button + **Done** button

**`notes_form_js` macro (JavaScript):**

*Before:* chips were rendered server-side and click handlers attached with `squadChips.forEach(...)`.

*After:* chips are rendered client-side by `renderTagChips()`, which:
- Iterates `availableTags` (loaded from `/api/tags`)
- In normal mode: clicking a chip toggles it selected (blue) / deselected (grey)
- In **Manage mode**: each chip gains a `×` button that calls `DELETE /api/tags/<name>`

New `loadTags()` is called in parallel with the existing `loadDimensionOptions()` at initialisation, then `renderTagChips()` runs before `loadNotes()` restores saved selections.

`setFormData()` now calls `renderTagChips()` instead of iterating `form.querySelectorAll('.squad-chip')`.

### UX flow

```
Normal view: [Shop] [Checkout✓] [Platform✓] [Loyalty]        [Manage]
                                                                  ↓ click
Manage mode: [Shop ×] [Checkout ×] [Platform ×] [Loyalty ×]  [Manage]
             [________________] [Add] [Done]
```

Clicking **×** deletes the tag from the library (not from saved notes).
Typing a name and clicking **Add** appends it and immediately shows the new chip.
Clicking **Done** exits manage mode.

---

## Files Changed

| File | Change |
|------|--------|
| `app/services/notes.py` | Added `get_tags()`, `add_tag()`, `delete_tag()`, `_get_tags_path()`, `_save_tags()` |
| `app/routes/main.py` | Added `list_tags`, `create_tag`, `remove_tag` routes under `/api/tags` |
| `app/templates/_macros.html` | Renamed field, removed hardcoded chips, added dynamic rendering + Manage/Add/Done UX |
| `docs/todo.md` | Marked item as done |

---

## Notes

- **Backward compatibility:** Existing `notes/_tags.json` is not required. `get_tags()` falls back to `SQUAD_OPTIONS` if the file is absent, so the original squad list still appears on first load.
- **No migration needed:** Saved notes store `squad_owners` as a plain string array; deleting a tag from the library does not modify those files.
- **Thread safety:** The tag file is small and write operations are synchronous. No locking is required at the single-process Flask dev server level; production deployments with Gunicorn workers could see a rare race on concurrent edits, which is acceptable for a low-frequency config file.
