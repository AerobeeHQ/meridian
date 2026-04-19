# v2-010 — Themes & Settings Page

## Goal

Give users control over the app's appearance via a Settings page. Phase 1 delivers System/Light/Dark theme switching with auto dark-mode for browsers that signal a preference. Phase 2 (future) adds the Adobe Spectrum theme.

---

## Phase 1 — System / Light / Dark

### Storage
- Key: `localStorage.codex-theme`
- Values: `"auto"` (default) | `"light"` | `"dark"`

### Theme application
- Bootstrap 5.3 `data-bs-theme` attribute on `<html>` drives built-in component theming.
- An inline `<script>` immediately before `</head>` reads localStorage and sets the attribute **before** paint to prevent FOUC.
- In `auto` mode a `MediaQueryList` listener keeps the attribute in sync with OS-level changes at runtime.
- A few custom CSS properties (navbar gradient, sticky-header background, table-hover colours, code backgrounds) are overridden for dark mode via a `[data-bs-theme="dark"]` block.

### Settings page
- Route: `GET /<client>/settings`  (`active_tab = 'settings'`)
- Template: `app/templates/settings.html` (extends `base.html`)
- A button-group of three options — **System**, **Light**, **Dark** — each with a descriptive icon.
- Selection is handled entirely in JavaScript; page does not require a form POST.
- A "Coming Soon" section previews the Adobe Spectrum theme.

### Navbar
- An inline SVG gear icon added to the right-side `navbar-nav`, linking to `/<client>/settings`. Inline SVG avoids adding Bootstrap Icons as a CDN dependency.
- Highlighted (`.active`) when `active_tab == 'settings'`.

---

## Phase 2 — Adobe Spectrum (future)

- Add `"spectrum"` as a fourth theme option.
- Load `@adobe/spectrum-web-components` via CDN when the theme is active (avoid loading for other themes).
- Apply Spectrum's `medium` scale and `light`/`dark` colour stop based on the resolved system preference.
- Map Spectrum's design tokens to Bootstrap's CSS custom-property overrides so non-Spectrum components (DataTables, custom selects) remain consistent.

### Reference
- Component library: https://opensource.adobe.com/spectrum-web-components/
- Contributor docs: https://github.com/adobe/spectrum-web-components/blob/main/CONTRIBUTOR-DOCS/README.md

---

## Files changed

| File | Change |
|------|--------|
| `app/templates/base.html` | Inline theme-apply script, dark-mode CSS overrides, navbar gear icon |
| `app/routes/main.py` | New `/<client>/settings` route |
| `app/templates/settings.html` | New settings page template |
| `docs/version-2-roadmap.md` | Add feature #10 to table and details section |
