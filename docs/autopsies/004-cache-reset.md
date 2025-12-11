# Fix: Clear Cache on Server Restart

**Date:** December 11, 2025  
**Issue:** Cached API responses persisted across server restarts, requiring manual cache deletion

## Summary
Updated the Flask app factory to clear the `cache/` directory whenever the server boots, ensuring fresh Adobe Analytics data is fetched instead of stale cached responses.

## Actions Taken
1. Imported `CacheService` in `app/__init__.py`.
2. Added a startup hook inside `create_app()` that instantiates `CacheService` and runs `clear_all()`, logging success or failure via `app.logger`.

## Verification
1. Attempted to run `python verify_setup.py` after the change (command executed but produced no console output in this environment; please rerun locally to confirm).

## Next Steps
1. Restart the Flask dev server (`python run.py`) and confirm `/events` immediately refetches data without manual cache cleanup.

