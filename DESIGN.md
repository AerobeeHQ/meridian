---
name: Codex
description: Adobe Analytics configuration intelligence — decoded, connected, authoritative.
colors:
  bg: "#0A0C10"
  surface: "#0F1117"
  surface-2: "#161B24"
  border: "#1E2533"
  border-2: "#2A3347"
  text-primary: "#E8EAF0"
  text-secondary: "#9AA3B2"
  text-muted: "#5E6B82"
  indigo: "#6366F1"
  violet: "#8B5CF6"
  blue: "#3B82F6"
  emerald: "#10B981"
  amber: "#F59E0B"
  rose: "#F43F5E"
  app-light-nav-start: "#4A82D4"
  app-light-nav-end: "#179F9B"
  app-dark-accent: "#D4622A"
typography:
  display:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "clamp(32px, 5.5vw, 60px)"
    fontWeight: 800
    lineHeight: 1.1
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "clamp(26px, 4vw, 36px)"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  body:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
  label:
    fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    fontSize: "12px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "0.1em"
  mono:
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "normal"
rounded:
  sm: "6px"
  default: "10px"
  lg: "16px"
  xl: "24px"
  pill: "100px"
spacing:
  xs: "8px"
  sm: "16px"
  md: "24px"
  lg: "32px"
  xl: "48px"
  2xl: "64px"
  3xl: "96px"
components:
  button-primary:
    backgroundColor: "{colors.indigo}"
    textColor: "#FFFFFF"
    rounded: "{rounded.default}"
    padding: "12px 24px"
  button-primary-hover:
    backgroundColor: "#5254CC"
    textColor: "#FFFFFF"
  button-ghost:
    backgroundColor: "{colors.surface-2}"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.default}"
    padding: "12px 24px"
  button-ghost-hover:
    backgroundColor: "#1F2535"
    textColor: "{colors.text-primary}"
  nav-cta:
    backgroundColor: "{colors.indigo}"
    textColor: "#FFFFFF"
    rounded: "{rounded.sm}"
    padding: "7px 16px"
  feature-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "32px"
---

# Design System: Codex

## 1. Overview

**Creative North Star: "The Analyst's Observatory"**

Codex is not a dashboard and it is not a reporting tool. It is an observatory: a precision instrument for practitioners who already know what they are looking for, and want to find it fast. The visual language reflects this. Dark canvas, indigo as the primary signal colour, a full categorical palette for the six variable types (indigo, violet, blue, emerald, amber, rose), Inter for reading and JetBrains Mono for data. The density is intentional; the interface trusts its users to read it.

The two surfaces, brochure and product app, share one voice. The brochure expresses the Observatory metaphor outward, with a star-field canvas, glowing orbs, and scrolling feature reveals. The product app expresses it inward, as a compressed, reference-weight tool where the data is the entirety of the point. Both dark. Both indigo. Both authoritative. Neither decorative.

This system explicitly rejects generic SaaS dashboard aesthetics: blue-gradient heroes with metric cards and "Transform your data" copy. It also rejects consumer-app warmth: rounded bubbles, pastel gradients, and emoji-heavy affordances. The wrong answer for Codex is anything that looks designed for someone who needs convincing. The right answer is designed for someone who already knows exactly what they need.

**Key Characteristics:**
- Dark-first: the base surface is near-black (#0A0C10), not charcoal grey
- Full categorical palette: six semantic accent colours, each assigned a variable type
- Indigo is the interactive signal: links, prompts, active states, progress, CTAs
- Monospace is the data language: JetBrains Mono for all variable names, values, and code
- Structural shadows, not decorative: cards always have a shadow; hover deepens it


## 2. Colors: The Observatory Palette

Dark canvas with an indigo primary signal and a deliberate full categorical palette. No accent appears without a reason.

### Primary
- **Station Indigo** (#6366F1): The primary interactive signal. Used on all links, active states, CTA buttons, progress bars, section labels, and the star icon in the hero badge. Also the grid-line colour in the hero at 4% opacity. The single loudest colour in the system.

### Secondary
- **Variable Violet** (#8B5CF6): Secondary accent, assigned to token/variable names in monospace contexts (`.t-keyword`, `.diagram-token`). Appears as a floating orb in the hero. Never used for primary interactive affordances.

### Tertiary
- **Config Blue** (#3B82F6): Applied to configuration key labels in the code snippet component. One of six categorical colours in the feature icon set.

### Neutral
- **Deep Space** (#0A0C10): The base background. Near-black with a cool blue-black tint; never pure black.
- **Observatory Floor** (#0F1117): Primary surface for sections and cards. Sits one step above the base.
- **Instrument Panel** (#161B24): Elevated surface for carousels, diagram cards, and active containers. Two steps above base.
- **Partition Line** (#1E2533): Primary border. Divides sections and wraps cards.
- **Elevated Partition** (#2A3347): Secondary border for elevated surfaces and badge outlines.
- **Primary Text** (#E8EAF0): Near-white body text. Warm-cool neutral.
- **Secondary Text** (#9AA3B2): Descriptions, captions, supplementary labels.
- **Muted Text** (#5E6B82): Tertiary labels, timestamps, section headers in uppercase.

### Categorical Accent Set
These four colours appear as feature category icons and semantic data indicators only. They are never used as primary CTAs or interactive signals.
- **Emerald** (#10B981): Active status indicators, success output, data feed column highlights.
- **Amber** (#F59E0B): Processing rules, warnings, badge-proc category.
- **Rose** (#F43F5E): Notes/annotations feature category.
- **Indigo-dim** (rgba(99, 102, 241, 0.12)): Indigo at 12% opacity; chip backgrounds, active tab fill, feature icon backgrounds. Never standalone.

### App Shell Dual-Theme Accents
The product app navbar carries a theme-specific gradient accent separate from the brochure's indigo primary:
- **Light-mode navbar:** #4A82D4 to #179F9B (blue to teal gradient, left to right)
- **Dark-mode navbar:** #D4622A to #9B2525 (burnt orange to crimson gradient)
- **Dark-mode links and buttons:** #D4622A / #E07040. These serve the same interactive signal role as indigo does on the brochure, within the Bootstrap-based app shell only.

### Named Rules
**The One Signal Rule.** Indigo (#6366F1) is the interactive signal on the brochure. Every element that can be clicked or is active uses indigo. The categorical colours (violet, blue, emerald, amber, rose) categorise, they do not call to action.

**The Tonal Layering Rule.** Depth within the dark theme is expressed through four tonal surface steps (bg / surface / surface-2 / terminal-bg #0D1117), not through drop shadows alone. Shadows reinforce; tonal steps establish.


## 3. Typography

**Display + Body Font:** Inter (weights 300–800), fallback system-ui/-apple-system
**Mono Font:** JetBrains Mono, fallback Fira Code, monospace

**Character:** Inter at its heavier weights (700–800) carries the observatory's authority, while JetBrains Mono makes variable names and configuration values feel like technical fact rather than prose. The pairing is standard at a glance and precise in use: the type never calls attention to itself, only to the data it contains.

### Hierarchy
- **Display** (800 weight, clamp(32px, 5.5vw, 60px), line-height 1.1, letter-spacing -0.03em): Hero headline only. Maximum one instance per surface. The statement.
- **Headline** (700 weight, clamp(26px, 4vw, 36px), line-height 1.2, letter-spacing -0.02em): Section titles (`section-title`). Sets the topic of each content block.
- **Title** (700 weight, 20px, line-height 1.3, letter-spacing -0.01em): Feature card headings, step panel headings. Named content within a section.
- **Body** (400 weight, 16px, line-height 1.6–1.7): All running prose, descriptions, subtitles. Max line length 65–75ch enforced on hero subtitle (max-width 600px) and section subtitle (max-width 640px).
- **Label** (600 weight, 12px, letter-spacing 0.1em, uppercase): Section overlines (`section-label`), footer column headings, diagram section labels. Always in indigo or muted text.
- **Mono** (400 weight, 13–13.5px, line-height 1.6): All variable names, config values, API keys, terminal output, and inline code. JetBrains Mono exclusively.

### Named Rules
**The Mono Contract.** Any value that came from an API, database, or configuration file is rendered in JetBrains Mono. No exceptions. Variable IDs, report suite identifiers, dimension names in data contexts, code output: all mono.

**The Scale Rule.** Every type step is at minimum 1.3x the step below it. No flat type scales. The jump from Label (12px) to Body (16px) to Title (20px) to Headline (36px) to Display (60px) is deliberate and maintained.


## 4. Elevation

The system uses structural shadows on the dark surfaces: cards always carry a shadow as a resting-state attribute, not just on hover. The dark background absorbs shadow well; even the heaviest shadow (0 12px 40px rgba(0,0,0,0.6)) reads as depth rather than decoration.

### Shadow Vocabulary
- **Shadow-sm** (`0 1px 3px rgba(0,0,0,0.4)`): Subtle grounding for inline elevated elements.
- **Shadow** (`0 4px 16px rgba(0,0,0,0.5)`): Default card-level depth at rest.
- **Shadow-lg** (`0 12px 40px rgba(0,0,0,0.6)`): Hover state on feature cards, resting state on carousel and diagram card. Maximum lift.
- **Inset ring** (`0 0 0 1px rgba(99,102,241,0.08–0.10) inset`): Applied to carousel and diagram card interiors. Gives a barely-visible indigo halo. Use sparingly and only on signature showcase elements.

### Named Rules
**The Structural Shadow Rule.** Cards rest with a shadow. Hover deepens the shadow and lifts the card (`translateY(-3px)` plus shadow-lg). Shadow is never added purely as decoration on a flat element that does not need elevation context.

**The Dark Absorption Rule.** On dark surfaces, heavy shadows (rgba 0.5–0.6) read clearly as depth, not heaviness. Do not translate these to light surfaces without re-evaluating the opacity values; shadows that read as depth on dark read as mud on light.


## 5. Components

### Buttons
Components pack information. Hover states are confident and immediate. Every button communicates its state clearly.

- **Shape:** Gently rounded (10px radius — `{rounded.default}`). Nav CTA uses tighter 6px radius.
- **Primary:** Indigo (#6366F1) background, white text, 12px/24px padding, weight 600, 15px size. Hover lifts 1px, background deepens to #5254CC, box-shadow adds indigo glow (`0 4px 20px rgba(99,102,241,0.4)`). Arrow icon inline-flex.
- **Ghost:** Surface-2 background (#161B24), secondary text (#9AA3B2), 1px border (border-2 #2A3347). Hover: background to #1F2535, text brightens to primary. No glow.
- **Nav CTA:** Identical to Primary but with sm radius (6px) and tighter padding (7px/16px). Used in navigation context only.

### Chips and Tags
- **Feature Tags:** Indigo-dim background (rgba(99,102,241,0.12)), indigo text (#6366F1), 1px border at rgba(99,102,241,0.2), pill radius (100px), 12px/500 weight, 4px/10px padding. Used to list capabilities inside feature cards.
- **Badge (categorical):** 11px/600 weight, 4px radius, coloured background at 15–20% opacity with matching text. Two variants: badge-action (indigo tinted) and badge-proc (amber tinted). Used in data lineage diagrams only.

### Cards and Containers
- **Feature Card:** Observatory Floor (#0F1117) background, 1px Partition Line border, 16px radius, 32px internal padding. Hover: border brightens to Elevated Partition, shadow deepens to shadow-lg, card lifts 3px.
- **Diagram Card:** Instrument Panel (#161B24) background, Elevated Partition border, 16px radius, shadow-lg always active plus indigo inset ring. Represents live data; always elevated.
- **Requirement Card:** Instrument Panel background, Partition Line border, 16px radius, 24px padding. No hover shadow — informational, not interactive.

### Inputs and Fields
- **Terminal Block:** #0D1117 background (one step below base), Elevated Partition border, 16px radius. macOS traffic-light dots (red #FF5F57, yellow #FEBC2E, green #28C840) in the title bar are decorative context markers only. All code is JetBrains Mono at 13–13.5px.
- **Config Snippet:** Same base as terminal. JSON keys in Config Blue (#3B82F6), string values in Emerald (#10B981), braces in secondary text.

### Navigation

**Brochure nav:** Fixed, 64px height, near-black background (rgba(10,12,16,0.85)) with 12px backdrop blur. Scrolling increases opacity to 0.97. Logo is Inter 700 17px. Nav links are 14px/500 in secondary text (#9AA3B2), hover brightens to primary text with a surface-2 background pill. Nav CTA is indigo with sm radius.

**App shell nav (Bootstrap):** Fixed, 56px height. Light mode: left-to-right gradient #4A82D4 to #179F9B. Dark mode: left-to-right gradient #D4622A to #9B2525. Navbar brand is 600 weight. All nav links are white with a text-shadow for depth. Active links are bold. The dark-mode accent (#D4622A, burnt orange) carries through to buttons, links, and focus indicators within the app shell.

### Table (Product App Signature Component)
The primary product surface. Bootstrap DataTables with Codex overrides.
- **Row hover (light):** #EFF4FA (pale blue tint). Row hover (dark): #2A3550 (deep blue-grey).
- **Selected row (light):** #D4E5F7. Selected row (dark): #1E3A5F.
- **Table links:** Light: #2C5282 (navy), no underline, 500 weight, 4px radius hover background at rgba(102,126,234,0.15). Dark: #90CDF4.
- **Sticky column headers:** z-index 2, top 56px (below fixed navbar), shadow line `0 1px 0 #dee2e6`.
- **Active search input outline:** Light mode: 2px #D4622A with orange glow. Dark mode: 2px #179F9B with teal glow. Signals the filter is live.


## 6. Do's and Don'ts

### Do:
- **Do** use indigo (#6366F1) as the single primary interactive signal on the brochure surface. One signal colour, used consistently for all clickable and active states.
- **Do** render all variable names, IDs, API values, and configuration data in JetBrains Mono. The mono face is the data face.
- **Do** apply structural shadows to cards. Cards rest at shadow; hover deepens to shadow-lg with 3px lift.
- **Do** use the categorical accent set (violet, blue, emerald, amber, rose) for categorisation and status only. Each colour names a type, not an interaction.
- **Do** maintain four tonal surface steps: bg (#0A0C10), surface (#0F1117), surface-2 (#161B24), terminal (#0D1117). Depth is expressed tonally before it is expressed with shadow.
- **Do** use the pill radius (100px) for chips, tags, and status badges. Use the default radius (10px) for buttons and tabs. Use lg (16px) for cards and containers.
- **Do** honour `prefers-reduced-motion`. All animations (orbFloat, pulse, scrollBounce, fadeIn) have a media query that collapses them to near-instant.
- **Do** cap prose line lengths at 65–75ch. Use `max-width` constraints on hero subtitle (600px) and section subtitle (640px).

### Don't:
- **Don't** use `background-clip: text` with a gradient. The existing `.hero-title-accent` (indigo-violet gradient text) is a known deviation; do not add new instances. Emphasis belongs to weight and size, not colour gradients on text.
- **Don't** use `border-left` greater than 1px as a coloured accent stripe on any list item, card, or callout. The `.diagram-assignment` border-left is a code indentation marker within a mock diagram, not a design pattern.
- **Don't** create generic SaaS-style hero sections: blue-gradient backgrounds, big metric numbers with small labels, "Transform your data" headline copy, grid-of-identical-feature-cards. This is what Codex explicitly is not.
- **Don't** apply consumer-app aesthetics: pastel gradients, rounded-bubble components, emoji-heavy labels, or illustration-driven empty states. Wrong register for a technical practitioner tool.
- **Don't** use pure black (#000) or pure white (#fff) anywhere. The base is #0A0C10, not black. Text primary is #E8EAF0, not white.
- **Don't** add decorative glass effects (backdrop-filter blur) outside the navigation bar. The nav blur is functional (legibility over the hero canvas). Elsewhere, blur is decoration.
- **Don't** translate the brochure's dark-mode shadow values directly to light-mode surfaces. rgba(0,0,0,0.5) is appropriate on #0A0C10; it is mud on #ffffff.
- **Don't** use the app shell's dark-mode orange accent (#D4622A) on the brochure surface. The two surfaces have different accent identities. Brochure: indigo. App-dark: burnt orange.
