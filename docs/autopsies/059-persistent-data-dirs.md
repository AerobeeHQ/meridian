# 059 — Persistent Data Dirs: Use CODEX_SECRETS_DIR

**Branch:** `fix/persistent-data-dirs-use-secrets-dir`
**Date:** 2026-04-22

---

## The bug

Two places in the codebase resolved their data directories relative to `__file__` (the Python source file location):

| Location | Hardcoded path |
|----------|---------------|
| `app/services/notes.py:13` | `{project_root}/notes/` |
| `app/__init__.py:66` | `{project_root}/cache/<client_slug>/` |

In local development this works fine — the project root is a persistent directory on the developer's machine.

In Docker, the application source code is copied *into the image* at build time. Any data written to `notes/` or `cache/` lands inside the container's overlay filesystem and is **wiped on every redeploy**. Users would lose all their dimension annotations after each release.

The bug was recorded in `docs/todo.md`:
> `notes.py` hard-codes the notes directory path relative to `__file__` — should use `CODEX_SECRETS_DIR` or an env-configured path for portability across deployments.

---

## The fix

Both directories now prefer `$CODEX_SECRETS_DIR/<subdir>` when the environment variable is set, falling back to the legacy project-root path for local development.

### `app/services/notes.py`

Extracted a `_resolve_notes_dir()` function:

```python
def _resolve_notes_dir() -> str:
    secrets_dir = os.environ.get('CODEX_SECRETS_DIR')
    if secrets_dir:
        return os.path.join(secrets_dir, 'notes')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'notes')

NOTES_DIR = _resolve_notes_dir()
```

### `app/__init__.py`

Changed `_build_client_services()` to read `CODEX_SECRETS_DIR` before falling back:

```python
_secrets_dir = os.environ.get('CODEX_SECRETS_DIR')
if _secrets_dir:
    cache_dir = os.path.join(_secrets_dir, 'cache', client_slug)
else:
    cache_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'cache', client_slug,
    )
```

---

## Why CODEX_SECRETS_DIR?

`CODEX_SECRETS_DIR` is already the single env var that must be set to run Codex (it points to the per-client JSON config files). In a Docker deployment it is typically a bind-mount, so anything stored alongside the secret configs survives container replacement.

No new env var is needed — co-locating `notes/` and `cache/` under the secrets directory is the natural place for persistent app data.

---

## Backwards compatibility

- If `CODEX_SECRETS_DIR` is **not set** (local dev, CI), the behaviour is identical to before.
- If `CODEX_SECRETS_DIR` **is set**, data migrates to the new location on the next write. Existing notes at the old location are not automatically moved — any existing Docker deployments would need a one-time manual copy of `notes/` into `$CODEX_SECRETS_DIR/notes/`. This is an acceptable trade-off given the alternative (permanent data loss on each deploy).

---

## Tests

Added `TestResolveNotesDir` in `tests/test_notes.py` with two cases:

| Test | What it checks |
|------|---------------|
| `test_uses_secrets_dir_when_env_is_set` | Returns `$CODEX_SECRETS_DIR/notes` when env var is present |
| `test_falls_back_to_project_root_when_env_not_set` | Returns a path ending in `/notes` when env var is absent |

All 131 tests pass.

---

## Files changed

| File | Change |
|------|--------|
| `app/services/notes.py` | Added `_resolve_notes_dir()`; `NOTES_DIR` now calls it |
| `app/__init__.py` | Cache dir resolved via `CODEX_SECRETS_DIR` with fallback |
| `tests/test_notes.py` | Added `TestResolveNotesDir` (2 tests) |
| `docs/todo.md` | Marked bug as done |
