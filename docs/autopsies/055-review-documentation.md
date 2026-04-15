# 055 — Review Documentation

**Date:** 2026-04-15
**Branch:** `copilot/review-documentation-and-add-guides`
**Status:** Complete

---

## Problem

The project documentation had drifted from the codebase after several significant architectural changes:

1. **Multisite routing** (PR #67 / autopsy 052) introduced per-client URL prefixes (`/<client>/`) and a `CODEX_SECRETS_DIR`-based secrets directory, replacing the single `config.json` model. The README still described the old single-config approach.
2. **Brochure site** (autopsy 054) moved the product landing page into Flask at `/`. The README project structure was not updated.
3. **`docs/release-summary.md`** had a "What's Next" section listing Marketing Channel Rules, Adobe Launch, and User OAuth Login as not-yet-started — all three had since been completed or scaffolded.
4. **`docs/version-2-roadmap.md`** still listed User OAuth Login as "Planned" when it had partial scaffolding in place.
5. No dedicated quick start guides existed — the README's Quick Start section was brief and didn't cover the new secrets directory model or Docker deployment in depth.

---

## Solution

### README.md

- **Quick Start:** Updated installation steps to use `CODEX_SECRETS_DIR` and a secrets directory instead of `config.json`.
- **Configuration:** Replaced the single `config.json` section with the secrets directory model; updated the example config.
- **Docker:** Updated to describe the `./secrets` volume mount approach.
- **Project Structure:** Added `config_loader.py`, `adobe_launch.py`, `git_info.py`, `app/static/brochure/`, `assets/swagger/`; added a URL Structure table showing the `/<client>/` prefix pattern.
- **Authentication:** Added a note about API 1.4 deprecation and automatic failover.
- **Roadmap:** Added Multisite routing and Brochure site to Completed list; updated Version History table.
- **Last updated date:** 2026-04-15.

### docs/release-summary.md

- Removed stale "What's Next" entries for Marketing Channel Rules and Adobe Launch (both completed).
- Added Multisite routing and Brochure site to the Architecture & Deployment section.
- Updated the Architecture at a Glance diagram to include the multi-client layer and Reactor API client.
- Updated "Last updated" to April 2026.

### docs/version-2-roadmap.md

- Changed User OAuth Login status from "Planned" to "Scaffolded".
- Updated the implementation order note to reflect that scaffolding is in place.

### docs/quick-start.md (new)

Step-by-step guide for developers running Codex locally:
- Prerequisites (Python 3.13+, uv)
- Clone, install, secrets directory setup, environment variable
- `uv run verify_setup.py` health check
- Run the app and navigate to `/<client>/`
- Adding a second client
- Troubleshooting table

### docs/quick-start-docker.md (new)

Step-by-step guide for system administrators deploying Codex via Docker:
- Prerequisites (Docker, Docker Compose V2)
- Get the code, create secrets directory, fill in credentials
- `docker compose up -d --build`
- Verify, view logs, stop/restart
- Volume mounts explained
- Adding a second client
- Nginx reverse proxy example
- Updating Codex
- Troubleshooting table

---

## Files Changed

| File | Change |
|------|--------|
| `README.md` | Updated Quick Start, Configuration, Docker, Project Structure, Roadmap, Version History sections |
| `docs/release-summary.md` | Fixed stale "What's Next"; added multisite/brochure to Architecture section |
| `docs/version-2-roadmap.md` | User OAuth Login status: Planned → Scaffolded |
| `docs/quick-start.md` | New — developer local setup guide |
| `docs/quick-start-docker.md` | New — system admin Docker deployment guide |
| `docs/autopsies/055-review-documentation.md` | New — this document |
