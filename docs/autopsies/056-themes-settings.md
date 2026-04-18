# 056 — Themes & Settings Page

**Branch:** `feature/themes-settings`
**Date:** 2026-04-18
**Roadmap item:** [v2-010](../plans/v2-010-themes-settings.md)

---

## What was built

### Theme system
- Theme preference stored in `localStorage` under key `codex-theme`.
- Three values: `"auto"` (default), `"light"`, `"dark"`.
- Bootstrap 5.3's `data-bs-theme` attribute on `<html>` drives all built-in component theming (buttons, cards, tables, modals, etc.) automatically.
- An inline `<script>` at the very top of `<head>` in `base.html` reads the stored preference and sets `data-bs-theme` **before** the first paint — preventing any flash of unstyled content (FOUC).
- In `auto` mode a `MediaQueryList` listener (registered in the footer script block) keeps the attribute in sync if the user changes their OS theme while the page is open.

### Dark mode CSS overrides
Custom styles in `base.html` that Bootstrap's `data-bs-theme` doesn't cover automatically:
- Footer border, text, and `<code>` background
- `.pre-code` text colour
- Table hover, selected row, and link colours
- Sticky-header background for `#dataTable thead th`
- Table stripe opacity
- Accordion open state
- Custom searchable-select dropdown backgrounds
- `.btn-secondary` colour overrides

### Settings page
- New route: `GET /<client>/settings` → `active_tab='settings'`
- New template: `app/templates/settings.html`
- Three theme buttons (System / Light / Dark) styled as Bootstrap button-group with SVG icons
- Active button highlighted via JS on load and on click; no page reload needed
- A "Coming Soon" card previews the Adobe Spectrum theme

### Navbar gear icon
- SVG gear icon in the right-side `navbar-nav`, linking to `/<client>/settings`
- Marked `.active` when `active_tab == 'settings'`

---

## Key decisions

### Bootstrap `data-bs-theme` over manual CSS variables
Bootstrap 5.3 ships with a complete dark-mode token system. Applying `data-bs-theme="dark"` to `<html>` handles ~90% of the theming automatically. The alternative (manual CSS custom properties throughout) would require maintaining parallel colour palettes for every component and would drift over time.

### localStorage (client-side) over server session
Theme is a per-browser, per-user preference that has no bearing on data fetching. Storing it client-side avoids a round-trip, works without auth, and doesn't require any schema changes.

### Inline head script for FOUC prevention
Any delay in applying the theme attribute (e.g. a `DOMContentLoaded` listener) results in a white flash before the dark background renders. The inline script runs synchronously before the browser paints anything.

### Adobe Spectrum — scaffolded as "Coming Soon"
The Spectrum Web Components library is non-trivial to integrate because it uses custom elements and its own design tokens that must be mapped to Bootstrap's CSS properties. It was explicitly requested as a future feature. The settings page reserves a card for it to make the intent visible without blocking Phase 1.

---

## Files changed

| File | Change |
|------|--------|
| `app/templates/base.html` | Inline theme-apply script in `<head>`, dark mode CSS overrides, gear icon in navbar, OS-change listener script |
| `app/routes/main.py` | New `/<client>/settings` route |
| `app/templates/settings.html` | New settings page |
| `docs/version-2-roadmap.md` | Added feature #10 |
| `docs/plans/v2-010-themes-settings.md` | New plan doc |
| `AGENTS.md` | Documented `CODEX_SECRETS_DIR=$(pwd)/secrets` in all run/verify commands |

---

## Future work (Phase 2)

- Add Adobe Spectrum theme: load `@adobe/spectrum-web-components` via CDN when selected, apply Spectrum tokens, map to Bootstrap CSS custom properties.
- Consider adding more appearance settings: compact/comfortable density, font size.
