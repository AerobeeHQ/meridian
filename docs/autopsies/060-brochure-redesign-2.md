# 060 — Brochure Redesign: The Webmaster's Reference

**Date:** 2026-05-01
**Branch:** feature/brochure-redesign-2

## What changed

Full rewrite of the brochure surface: `app/templates/brochure.html`, `app/static/brochure/css/style.css`, `app/static/brochure/js/main.js`. New design system documents: `PRODUCT.md`, `DESIGN.md`.

## Why

The first brochure iteration failed the "AI-generated aesthetic" test — a teenager immediately clocked it as machine-made. The dark background, indigo/violet palette, hero-metric cards, smooth card grids, and Google Fonts were every generic SaaS landing page pattern stacked on top of each other.

## Design direction chosen

**North Star: "The Webmaster's Reference"**

Two distinct surface identities that share hue family and font stack but resolve tokens independently:

- **Brochure:** Personal domain circa 2001–2005. Cisco 2008 structural language: light background (near-white), horizontal nav strip in institutional blue, panel blue-gray (`#dce8f0` territory) content zones, hard 1px borders, pipe-separated footer. Georgia serif for headings, Verdana for body. Feature list as a two-column `<dl>` spec sheet — not a card grid.
- **App (future):** jQuery UI Themeroller desktop-in-browser. Dense, hard-bordered panels with drag chrome, beveled title bars, structural drop shadows, status bar. Every affordance visible.

## Key decisions

**Rejected patterns:**
- Google Fonts (removed preconnect/link tags) — system fonts only. Georgia + Verdana are the most period-correct pairing for this aesthetic and need no network round-trip.
- Star canvas / hero orbs / animated entrance effects — stripped entirely.
- Hero-metric cards ("10+ config types") — replaced with a two-column image hero.
- Card grid for features — replaced with `<dl class="feature-list">` with `grid-template-columns: 26ch 1fr`, styled like a spec sheet with ruled rows.
- `target="_blank"` on nav links — tabbed browsing was not standard in 2005. Period-correct omission.
- `border-radius` > 4px — anachronistic for the Themeroller / Cisco 2008 era.
- Diffuse modern drop shadows — structural hard shadows only.

**Kept patterns:**
- Screenshot carousel with progress bar, keyboard/touch/hover pause — unchanged.
- Step tabs for getting-started section — unchanged.

**Removed patterns:**
- IntersectionObserver scroll reveal (`animate.js` / `.observe` / `.visible` rules) — stripped entirely. All entrance animation CSS removed from `style.css`. The `main.js` rewrite does not create an IntersectionObserver. Sections are visible immediately on load, matching the period-correct "documents appear instantly" aesthetic of the reference era.

**Color system:**
OKLCH custom properties. Near-white page background (`oklch(99% 0.003 220)`), panel blue-gray surface (`oklch(94% 0.016 222)`), institutional web-era blue primary (`oklch(42% 0.145 264)`), dark nav strip (`oklch(32% 0.07 255)`). Chroma kept low on neutrals, high only on primary/accent.

**Hero:**
Two-column grid: left column text + CTAs, right column `codex-hero.png` (1169×663, the existing marketing screenshot). `loading="eager" decoding="async"` on the hero image. Alt text only, no caption.

**Typography:**
Georgia for brochure headings only (Display → Headline → Title hierarchy). Verdana everywhere else. Body line-length capped at 68ch. No Georgia in app — this is a hard rule encoded in DESIGN.md.

## What the DESIGN.md seed established

Six-section design spec (Overview, Colors, Typography, Elevation, Components, Do's and Don'ts) with named rules:
- **The Two-Surface Rule:** brochure and app do not share a stylesheet.
- **The Georgia-Only-on-Brochure Rule:** Georgia never appears in the app.
- **The Hard Shadow Rule:** app shadows are structural (2–4px offset, visible direction), not diffuse (24px+ blur, near-zero offset).

## What the PRODUCT.md update established

Added `register: both` field. Named surface personalities: "Personal Webmaster" (brochure) and "jQuery UI Themeroller" (app). Anti-references updated to explicitly call out AI-generated aesthetic and modern flat design in the app. Five design principles formalized.

## Lessons

- The fastest way to fail the AI-slop test is to reach for Google Fonts, a dark background, indigo gradient, and card grid. These four choices together are sufficient to fail.
- Period-correct choices are an effective strategy against AI-generic defaults — they require specific historical knowledge the generic training-data reflex doesn't have.
- The `<dl>` spec-sheet layout for features is a strong alternative to card grids: it reads like reference material, not marketing copy, which matches the "practitioner's reference" brand position.
- Seeding DESIGN.md before implementation forces explicit design decisions before they get made implicitly by CSS defaults.
