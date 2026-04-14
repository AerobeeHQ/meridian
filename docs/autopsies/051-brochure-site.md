# 051 — Brochure Site

**Date:** 2026-04-13
**Branch:** `feature/brochure-site`
**Status:** Complete

---

## Problem

Codex had no public-facing presence beyond the application itself. A product brochure site was needed to communicate the project's value proposition, features, and getting-started instructions — to be hosted on Cloudflare Pages as a static site.

---

## Solution

### Generator choice — staticjinja

Uses `staticjinja` (v5.0.0), which is a widely-documented static site generator. `staticjinja` uses Jinja2 templates, renders them to an output directory, and optionally watches for changes during development.

**Note:** The `staticpaths` parameter (for copying static assets) was deprecated in `staticjinja` 5.x and triggers a warning. The build script uses `shutil.copytree` to copy the `static/` folder to `output/static/` before rendering.

### Site structure

```
site/
├── templates/index.html   # Single Jinja2 template — the full page
├── static/css/style.css   # All styles (~550 lines)
├── static/js/main.js      # Mobile nav, step tabs, scroll animations
├── build.py               # Build script (one-shot + --watch mode)
├── pyproject.toml         # staticjinja dependency, managed by uv
└── README.md              # Local run and Cloudflare deploy instructions
```

Compiled output goes to `site/output/` (git-ignored). The user builds locally and pushes the compiled files to Cloudflare Pages manually.

### Design approach

**Theme:** Dark, high-contrast design (`#0A0C10` background) with an indigo/violet accent (`#6366F1`/`#8B5CF6`). Chosen to feel modern and technical without being generic — close to the aesthetic of developer tooling landing pages.

**Typography:** Inter (body) and JetBrains Mono (code blocks) via Google Fonts.

**Sections:**
1. **Hero** — Full-viewport with animated background orbs, grid overlay, headline with gradient accent text, CTA buttons, and a stats bar (10+ config types, 3 API integrations, v2)
2. **Trust bar** — Adobe product names as social proof
3. **Features** — 6-card grid (2-wide + 4 single), each with a colour-coded icon, description, and tag chips for the wide card
4. **Data Lineage** — Two-column layout: bullet list on the left, animated "mock detail panel" diagram on the right showing how a dimension is cross-referenced
5. **Getting Started** — Tabbed step panel (Clone → Configure → Run) with styled terminal blocks and a syntax-highlighted config snippet
6. **Requirements** — 2-column card grid
7. **Footer** — Brand, product links, and resource links

**Responsive:** Full mobile layout at 768px (single column, hamburger nav) and 480px (stacked buttons, compact stats).

**Animation:** CSS `transition` + `IntersectionObserver` for scroll-triggered fade-in on feature cards, lineage items, and requirement cards. A `--delay` CSS custom property staggers the animations per element index.

### Build script

```python
from staticjinja import Site
import shutil

shutil.copytree("static", "output/static")  # copy assets
site = Site.make_site(searchpath="templates", outpath="output")
site.render(use_reloader=USE_RELOADER)       # --watch flag for dev
```

### Deployment

Two paths documented in `site/README.md`:
- **Wrangler CLI**: `wrangler pages deploy output/ --project-name codex-site`
- **Cloudflare Dashboard**: drag-and-drop `output/` folder

No Cloudflare build step is configured — the user builds locally.

---

## Challenges

### 1. Package name mismatch

The prompt referenced `staticninja`. PyPI returns 404 for that name. The correct package is `staticjinja` — same project, correct PyPI name. Updated `pyproject.toml` and `build.py` accordingly.

### 2. Deprecated `staticpaths` API

`staticjinja` 5.x deprecated the `staticpaths` parameter (previously used to copy static directories). The replacement (`Make`) is more complex. Since the site only needs a one-time copy, `shutil.copytree` was used directly in `build.py` — simpler and more explicit.

### 3. Scroll animation vs. full-page screenshots

The `IntersectionObserver` fade-in approach sets `opacity: 0` on elements and transitions them to `opacity: 1` when they enter the viewport. Full-page screenshots (taken by Playwright) render the entire page without a real viewport scroll, so observers don't fire and elements remain invisible.

Fixed by exposing the animation via a CSS class (`.observe` / `.observe.visible`) driven by a `--delay` custom property, and manually calling `classList.add('visible')` via `browser_evaluate` before taking the screenshot. The screenshot was saved to `assets/screenshots/site-brochure.png`.

### 4. Screenshot working directory

The Playwright MCP tool resolved relative screenshot paths against the tool's working directory (the user's home folder), not the project root. Resolved by passing an absolute path.

---

## Files Changed

| File | Change |
|------|--------|
| `site/pyproject.toml` | New — `staticjinja` dependency, Python 3.11+ |
| `site/build.py` | New — build script with `--watch` flag |
| `site/templates/index.html` | New — full single-page Jinja2 template |
| `site/static/css/style.css` | New — ~600 lines of CSS (dark theme, responsive) |
| `site/static/js/main.js` | New — mobile nav, step tabs, IntersectionObserver animations |
| `site/.gitignore` | New — ignores `output/`, `.venv/`, `uv.lock` |
| `site/README.md` | New — local run and Cloudflare Pages deploy instructions |
| `assets/screenshots/site-brochure.png` | New — full-page screenshot for PR |
| `docs/autopsies/051-brochure-site.md` | New — this document |

---

## Notes

- The `output/` directory is git-ignored and must be built locally before deploying.
- The site is fully self-contained — no build dependencies on Cloudflare's side.
- Google Fonts are loaded via CDN; the site requires an internet connection to render correctly (acceptable for a brochure site, not an offline app).
- The live demo link (`https://codex.maxisdev.com`) is hardcoded in the HTML. Update if the URL changes.
