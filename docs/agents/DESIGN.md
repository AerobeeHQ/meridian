<!-- SEED — re-run /impeccable document once there's code to capture the actual tokens and components. -->

---
name: Meridian
description: The living data dictionary for Adobe Analytics — built by a practitioner, for practitioners.
---

# Design System: Meridian

## 1. Overview

**Creative North Star: "The Webmaster's Reference"**

Two surfaces. One voice. Distinct visual identities.

The brochure is a senior practitioner's personal domain — the kind of site a Webmaster circa 2002 would have built with care in Dreamweaver or GoLive. Light background, Georgia headings, Verdana body text, a horizontal navigation strip in web-era blue, hard-edged panel zones, and a visible structural grid. Nothing is there by accident; nothing is there to impress. Tonal reference: Cisco.com 2008 and its contemporaries — structured, professional, explicitly organized, handmade in the best sense.

The app is the workshop behind the reference. It feels like purpose-built desktop software running in a browser — jQuery UI Themeroller era: floating panels with drag chrome, tab strips, hard drop shadows, a status bar at the bottom. Dense, capable, every affordance visible. No whitespace wasted. The experience should feel like opening a well-configured application, not loading a web page.

This system explicitly rejects the AI-generated aesthetic that a teenager can clock in three seconds: smooth symmetric layouts, indigo or violet gradient palettes, star canvas backgrounds, scroll-reveal card grids, hero-metric templates. It rejects generic SaaS landing pages (hero-metric cards, "Transform your data" copy, Vercel/Stripe/Linear visual language), consumer-app playfulness (pastel gradients, rounded bubbles, emoji-heavy UI), and the modern flat-design school's borderless, spacious, depth-free aesthetic in the app.

**Key Characteristics:**
- Light background on the brochure; warm-gray chrome on the app
- Georgia serif headings on the brochure only; Verdana everywhere else
- Web-era blue (#0055a5 territory) as the structural and primary accent color
- Visible 1px solid borders, hard section dividers, explicit zone labels
- Dense windowed layout in the app; structured editorial grid on the brochure
- Motion restrained to state changes only — no scroll choreography, no entrance animations

## 2. Colors: The Web-Era Blue Palette

Two coordinated palettes sharing a hue family. The brochure uses blue-on-white in the structural tradition of professional early-2000s corporate web design. The app chrome is warm gray with the same blue family used for selection states, active tabs, and panel title bars.

### Brochure Surface — Primary
- **Web-Era Blue** [to be resolved during implementation — target: #0055a5 territory]: Navigation strip background, link color, primary CTA button. A real institutional blue, not indigo. The link color appears underlined at rest — this is intentional.
- **Navigation Blue** [to be resolved — target: #2a5f8f territory]: The horizontal nav strip and utility bar. Slightly darker than the primary link blue.

### Brochure Surface — Neutral
- **Clean White** [to be resolved — target: near #ffffff]: Page background. No tint; the period aesthetic used clean white.
- **Panel Blue-Gray** [to be resolved — target: #dce8f0 territory]: Background tint for card and content zone areas. The visual signature of this era — a cool blue-gray that marks a structured block of content.
- **Near-Black Body** [to be resolved — target: #1a1a1a]: Body text. Warm-tinted, never pure black.
- **Muted Gray** [to be resolved — target: #555555]: Secondary text, metadata, captions, pipe-separated footer links.
- **Rule Blue-Gray** [to be resolved — target: #b8ccd8]: Borders, horizontal rules, table dividers.

### App Surface — Chrome
- **Warm Panel Gray** [to be resolved — target: #f0ede6 territory]: Panel body background. Warmer than system gray; avoids the cold Ext-JS default.
- **Panel Title Bar Blue** [to be resolved — target: #3d6b9e, the brochure blue darkened]: Panel title bar gradient. Same hue family as brochure; signals the surfaces are related.
- **Panel Border** [to be resolved — target: #a8b8c8]: Hard 1px borders on all panels, no softening.
- **App Body Text** [to be resolved — target: #333333]: Dense UI text in Verdana at 12–13px.
- **Selection Blue** [to be resolved — same as brochure primary]: Active tab, selected table row, focused element.
- **Status Bar Gray** [to be resolved — target: #e0ddd6, slightly darker than panel gray]: The status bar at the very bottom.

**The Two-Surface Rule.** The brochure and app do not share a stylesheet. They share a hue family and a font stack, but their color values, spacing, and chrome are resolved independently. Never use a brochure token in app CSS or vice versa.

## 3. Typography: The Webmaster Stack

**Display and Heading Font:** Georgia (with Times New Roman, serif fallback)
**Body and UI Font:** Verdana (with Arial, Helvetica, sans-serif fallback)

**Character:** Georgia was designed to be beautiful on screen at display sizes; Verdana was designed to be legible in UI contexts at 11–13px. Together they are the most authentically period-correct pairing for this aesthetic — used by every high-craft personal and professional site of the Webmaster era, and still the most honest choice for what this project is doing.

### Hierarchy

- **Display** (Georgia, 700, clamp(2.2rem, 5vw, 3.8rem), line-height 1.1): Brochure hero heading only. Large, confident, tight letter-spacing.
- **Headline** (Georgia, 700, 1.6–2rem, line-height 1.2): Brochure section titles, feature headings.
- **Title** (Georgia, 400–600, 1.1–1.3rem, line-height 1.35): Brochure sub-headings. In the app, Verdana bold 13px is used for panel title bars instead.
- **Body** (Verdana, 400, 14–16px on brochure / 12–13px in app, line-height 1.6): Primary reading text. Cap at 70ch on the brochure.
- **Label** (Verdana, 400–600, 11–12px, normal case): Navigation items, field labels, status bar text, column headers. Never forced uppercase in the app — Verdana at small sizes reads clearly without it.

**The Georgia-Only-on-Brochure Rule.** Georgia is strictly the brochure's heading typeface. It does not appear in the app. The app uses Verdana for everything: panel titles, labels, table headers, body text, buttons. Mixing Georgia into the app chrome breaks the desktop-software illusion.

## 4. Elevation

The two surfaces have different elevation philosophies.

**Brochure:** Flat-by-default. Sections are separated by 1px solid borders and `#dce8f0`-tinted background zones, not shadows. Primary CTA buttons may carry a tight inset shadow to suggest pressability. No dramatic drop shadows anywhere on the brochure.

**App:** Structural depth. Panels float over the page surface with a hard drop shadow — tight offset, moderate spread, visible direction (`box-shadow: 2px 3px 6px rgba(0,0,0,0.35)` territory). Nested or elevated panels use a slightly stronger shadow. The shadow communicates panel stack order, not atmosphere. Dialog panels cast the strongest shadow.

**The Hard Shadow Rule.** Drop shadows in the app are structural, not decorative. The modern diffuse shadow (`blur: 24px+, offset near zero`) is prohibited in the app. It belongs to the flat-design era. In the desktop-software metaphor, shadows have direction and weight — you know which panel is on top.

## 5. Components

Components will be defined during the scan-mode pass once implementation begins. Two signature component patterns are established in principle:

**Brochure — Structured Content Zone:** A content block with `#dce8f0`-tinted background, `1px solid #b8ccd8` border, no border-radius or minimal 2px, internal padding matching the grid. Used for feature summaries, link clusters, callout blocks. Never nested. The visual unit of the brochure page.

**App — Floating Panel:** A draggable, collapsible panel with a blue-gradient title bar (Verdana 12px bold, white text, grip icon on the left, close X on the right), 1px solid border, hard drop shadow, and a white content body. Resizable. Panel position and open/closed state saved to localStorage per user. This is the signature UI component of the app — everything in the app lives in or relates to a panel.

## 6. Do's and Don'ts

### Do:
- **Do** use Georgia exclusively for brochure headings. Its serifs on screen at large sizes carry the period warmth and authority.
- **Do** use Verdana at 12–13px for all app UI text — it was designed for this density and reads cleanly at sizes where Inter or similar fonts become unclear.
- **Do** render borders at exactly 1px solid. No 0.5px, no fake borders via `box-shadow inset`, no blurred borders.
- **Do** make links look like links on the brochure: underlined by default, blue (#0055a5 family), hover darkens. This is correct behavior, not a mistake to be styled away.
- **Do** use hard 2–4px offset drop shadows in the app panels. They signal elevation the way this visual language expects.
- **Do** include a status bar at the bottom of the app with cache state, record count, and last-updated timestamp.
- **Do** save panel positions and collapse state to localStorage and restore them on page load.
- **Do** use `#dce8f0`-adjacent tints for brochure content zones — the blue-gray panel background is the visual signature of this era done well.
- **Do** separate footers with pipe characters (`|`) on the brochure: "Contacts | Feedback | Help | Site Map". This is period-correct and communicates density without clutter.

### Don't:
- **Don't** use the AI-generated aesthetic: indigo/violet gradients, star canvas backgrounds, hero-metric cards ("10+ config types"), scroll-reveal card grids, symmetric asymmetric grids. If a teenager can clock it in three seconds, it has failed.
- **Don't** use Georgia in the app. Not for panel titles, not for table headers, not anywhere.
- **Don't** use Verdana for brochure headings. It is a UI font, not a display font.
- **Don't** use `border-radius` greater than 4px anywhere in the app. The Themeroller era used 3–4px on buttons or none at all. Modern pill shapes and large radius values are anachronistic.
- **Don't** use diffuse modern drop shadows (`blur: 24px+, near-zero offset`). They have no place in the desktop-software metaphor.
- **Don't** use gradient text (`background-clip: text`) anywhere. Single solid color on all text.
- **Don't** use `border-left` greater than 1px as a colored accent stripe on cards or list items. This is the side-stripe anti-pattern — use full borders, background tints, or nothing.
- **Don't** use a dark background for the brochure. The Cisco 2008 reference is light-background and explicitly so. Dark is not period-correct for this aesthetic.
- **Don't** share stylesheets between the brochure and the app. They are resolved independently.
- **Don't** use SaaS landing-page patterns: "Transform your data" copy, Vercel/Stripe/Linear visual language, identical icon-heading-text card grids, glassmorphism.
