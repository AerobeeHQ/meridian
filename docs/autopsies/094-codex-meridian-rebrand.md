# 094 — Codex → Meridian Rebrand (Codebase)

**Date:** 2026-07-11
**Branch:** `rebrand/meridian-94`
**Status:** Complete (Issue #94 only)

---

## Problem

The product is being renamed from **Codex** to **Meridian** to avoid confusion
with OpenAI's Codex. Issue #94 covers the *codebase* portion of the rebrand
(display name is **Meridian**, slug/config-key form is `meridian`, new domain is
`meridian.aerobee.com.au`). Infrastructure (#95), promo assets (#96),
testing/cutover (#97), and the GitLab repo rename (#98) are manual/GUI phases
owned by Joris and were explicitly **out of scope** for this agent.

---

## What changed

### Environment variables (hard rename — decided with the user)
`CODEX_SECRETS_DIR`, `CODEX_CACHE_DIR`, `CODEX_NOTES_DIR`, `CODEX_SESSION_SECRET`
→ `MERIDIAN_*`. No fallback to the old names. Updated in `app/`, `verify_setup.py`,
`config.dist.json`, `docker-compose.yml`, `run_configurations/`, and the tests.

> **Deployment impact:** the running LXC container and any local shell profile must
> switch to `MERIDIAN_*` in lockstep, or the app won't start. This is part of #95.

### Internal identifiers
`app.codex_clients` → `app.meridian_clients`, `codex_api_service_v14` →
`meridian_api_service_v14`, `CODEX_CLIENT_SLUGS` → `MERIDIAN_CLIENT_SLUGS`.

### Front-end storage/theme keys
`data-codex-theme` → `data-meridian-theme`, and the `localStorage` keys
`codex-theme` / `codex-listing-search` → `meridian-*`. Existing users lose their
saved theme/search selection once (keys changed) — acceptable, non-breaking.

### Display strings
`Codex` → `Meridian` across templates, `run.py`, `verify_setup.py`, `Dockerfile`,
`Makefile`, `docker-build.sh`, `DESIGN.json`, docstrings, and `pyproject.toml`
(`name = "meridian"`, which re-locked `uv.lock`). Brochure `<title>`/OG/Twitter
meta now read "Meridian - Adobe Analytics Intelligence".

### Assets
`git mv` of `app/static/codex-logo.svg` → `meridian-logo.svg` and
`app/static/brochure/img/codex-hero.png` → `meridian-hero.png`, with template
references updated. The *visual* redesign of these assets remains #96.

### Docs
Rebranded current-facing docs (README, AGENTS, PRODUCT, DESIGN, quick-starts,
testing, roadmaps, plans). The old live-demo domain `codex.maxisdev.com` →
`meridian.aerobee.com.au`; example secrets paths and nginx/OAuth example domains
updated for consistency.

---

## Deliberately left unchanged

- **`docs/autopsies/`, `commits.txt`, `docs/handoff.md`, `docs/prompts.md`** —
  historical records; rewriting them would falsify history.
- **Repository slug URLs** — `github.com/aerobeehq/codex`, `git clone …/codex.git`,
  `cd codex`, and the `codex/` repo-root references. The GitLab/GitHub project is
  not renamed until **#98** (redirects preserved), so changing these now would
  produce dead links / 404s. **Update these during #98.**

---

## Verification

- `uv run pytest` → **172 passed**.
- `uv run verify_setup.py` → all checks pass, banner reads "Meridian Setup Verification".
- Manual smoke test on `http://127.0.0.1:5010`: brochure `<title>` = "Meridian -
  Adobe Analytics Intelligence"; app pages render with zero "Codex" strings; the
  only remaining `codex` tokens are the intentionally-preserved repo URLs.

---

## Follow-ups for later phases

- #95: update `MERIDIAN_*` env vars in the LXC container and deployment tooling.
- #96: replace the (still Codex-era) logo/hero art now living under the renamed files.
- #98: after the repo rename, update the `aerobeehq/codex` URLs and `cd codex`
  references in `app/templates/brochure.html` and the quick-start docs.
