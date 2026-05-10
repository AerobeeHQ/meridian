# 060 — Notes & Tags broken in Docker: read-only secrets volume

**Branch:** `fix/notes-writable-docker-volume`
**Date:** 2026-05-10
**Status:** Complete

---

## The bug

On Prop, eVar, and Event detail pages, the Documentation Notes form displayed
"Failed to save" whenever a user tried to save notes, and the "Manage →
Add" tag flow appeared to do nothing (no error, no new chip).

---

## Root cause

`docker-compose.yml` mounted the secrets directory **read-only**:

```yaml
volumes:
  - ./secrets:/app/secrets:ro   # ← read-only
environment:
  - CODEX_SECRETS_DIR=/app/secrets
```

`notes.py` resolves the notes storage directory as
`$CODEX_SECRETS_DIR/notes` (`/app/secrets/notes` inside the container).
When any write was attempted — saving a note, adding or deleting a tag —
the OS threw a `PermissionError` because the bind-mount disallows writes.

Flask's default error handler converted the unhandled exception to a
**500 HTML** response.  The JavaScript fetch chain called `response.json()`
on that HTML body, which threw a `SyntaxError`, which was caught by:

- `saveNotes()` → `.catch` → `statusEl.textContent = 'Failed to save'`
- `doAddTag()` → `.catch` → `console.error(...)` (no visible UI message)

---

## Why the read-only flag was there

`./secrets` contains per-client JSON credentials.  Mounting it read-only
is sensible for protecting those files — the app only needs to *read* them.
The mistake was using the same directory as the write destination for notes
and tags, which are user-generated data, not configuration.

---

## Fix

### 1. `app/services/notes.py` — new `CODEX_NOTES_DIR` env var

`_resolve_notes_dir()` now checks three locations in priority order:

| Priority | Source | Typical value |
|----------|--------|---------------|
| 1st | `$CODEX_NOTES_DIR` | `/app/notes` (Docker) |
| 2nd | `$CODEX_SECRETS_DIR/notes` | legacy fallback |
| 3rd | `{project_root}/notes` | local dev |

```python
def _resolve_notes_dir() -> str:
    notes_dir = os.environ.get('CODEX_NOTES_DIR')
    if notes_dir:
        return notes_dir
    secrets_dir = os.environ.get('CODEX_SECRETS_DIR')
    if secrets_dir:
        return os.path.join(secrets_dir, 'notes')
    return os.path.join(os.path.dirname(...), 'notes')
```

Also tightened `_ensure_notes_dir()` to use `exist_ok=True`, eliminating
a TOCTOU race on multi-worker deployments:

```python
# Before
if not os.path.exists(NOTES_DIR):
    os.makedirs(NOTES_DIR)

# After
os.makedirs(NOTES_DIR, exist_ok=True)
```

### 2. `docker-compose.yml` — dedicated notes volume

```yaml
volumes:
  - ./secrets:/app/secrets:ro   # config files — still read-only
  - ./exports:/app/exports:rw
  - ./cache:/app/cache:rw
  - ./notes:/app/notes:rw       # NEW: persistent notes storage
environment:
  - CODEX_SECRETS_DIR=/app/secrets
  - CODEX_CACHE_DIR=/app/cache
  - CODEX_NOTES_DIR=/app/notes  # NEW
```

The secrets volume remains read-only; user data lives in its own
bind-mount that is explicitly read-write.

---

## Backwards compatibility

| Deployment | Behaviour |
|-----------|-----------|
| Docker (new docker-compose) | Notes written to `/app/notes` via `CODEX_NOTES_DIR` |
| Docker (old docker-compose, no `CODEX_NOTES_DIR`) | Falls back to `$CODEX_SECRETS_DIR/notes` — still broken if secrets is `ro`; operators should add the new volume |
| Local dev (`CODEX_SECRETS_DIR=$(pwd)/secrets`) | Falls back to `secrets/notes/` — unchanged |
| Local dev (no env vars) | Falls back to `{project_root}/notes/` — unchanged |

Existing note JSON files are not moved automatically.  Docker operators
upgrading from the old layout should copy `./secrets/notes/` →
`./notes/` once before redeploying.

---

## Files changed

| File | Change |
|------|--------|
| `app/services/notes.py` | `_resolve_notes_dir()` checks `CODEX_NOTES_DIR` first; `_ensure_notes_dir()` uses `exist_ok=True` |
| `docker-compose.yml` | Added `./notes:/app/notes:rw` volume and `CODEX_NOTES_DIR=/app/notes` env var |
| `tests/test_notes.py` | Expanded `TestResolveNotesDir` — 4 tests covering all three resolution steps |
| `docs/todo.md` | Marked bug as resolved |

---

## Tests

`TestResolveNotesDir` now has four cases:

| Test | What it checks |
|------|---------------|
| `test_uses_notes_dir_env_var_first` | `CODEX_NOTES_DIR` wins when both vars are set |
| `test_notes_dir_takes_priority_over_secrets_dir` | Same, different paths |
| `test_uses_secrets_dir_when_notes_dir_not_set` | Legacy fallback to `$CODEX_SECRETS_DIR/notes` |
| `test_falls_back_to_project_root_when_no_env_vars_set` | Local dev fallback |

All 154 tests pass.
