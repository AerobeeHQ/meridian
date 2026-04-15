# 054 — Brochure Site Moved Into Flask (Retire staticjinja)

**Date:** 2026-04-15
**Branch:** `feat/serve-brochure-from-flask`

---

## Problem

The `site/` directory used `staticjinja` as a build step to render a single Jinja2 template into a static HTML file, then deployed that output separately to Cloudflare Pages. The template contained no Python logic or dynamic variables — staticjinja was a pure file-copy pass-through. This created unnecessary friction:

- A separate build step (`uv run build_site.py`) before each deploy
- A separate Cloudflare Pages project to manage
- Cross-origin "Live Demo" links pointing at `codex.maxisdev.com`
- Two deployment targets to keep in sync

The brochure site and the Codex application were conceptually one product, hosted separately for no technical reason.

---

## Solution

Retire `staticjinja` entirely. Move the brochure site directly into the Flask application:

- **Static assets** (`css/`, `js/`, `img/screenshots/`) → `app/static/brochure/`
- **Template** → `app/templates/brochure.html`
- **Root route** at `/` now calls `render_template('brochure.html')` instead of redirecting to the first client slug
- **Client apps** continue to live at `/<client_slug>/` as before

All "Live Demo" links in the brochure template were updated from the absolute Cloudflare URL (`https://codex.maxisdev.com/maxis/`) to the relative path `/maxis/`. Static asset `href`/`src` attributes were updated to use Flask's `url_for('static', filename='brochure/...')`.

---

## Files Changed

| Action | Path |
|--------|------|
| Deleted | `site/` (entire directory — build script, pyproject, templates, static, output) |
| Added | `app/static/brochure/css/style.css` |
| Added | `app/static/brochure/js/main.js` |
| Added | `app/static/brochure/img/screenshots/*.webp` (18 images) |
| Added | `app/templates/brochure.html` |
| Modified | `app/__init__.py` — root route now renders `brochure.html` |

---

## Deployment Impact

- The Cloudflare Pages project (`codex-site` / `codex.maxisdev.com`) can be retired
- DNS for `codex.maxisdev.com` should be updated to point at the Docker VM (or a reverse proxy in front of it)
- No changes to Docker or docker-compose — `app/` is already fully copied into the image
- No `site/` build step needed; everything ships with `docker compose up --build`

---

## URL Structure (After)

| Path | Content |
|------|---------|
| `/` | Brochure site (served by Flask) |
| `/<client>/` | Client overview dashboard |
| `/<client>/evars` | eVar listing |
| `/<client>/...` | All other Codex routes |
