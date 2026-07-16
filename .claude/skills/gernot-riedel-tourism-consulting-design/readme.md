# Gernot Riedel Tourism Consulting — Design System

KI-unterstützter Consultant für Tourismus (TVBs, DMOs, Hotels; DACH, alpine Destinationen). 30+ Jahre Praxis als Tourismusmanager (Kitzbüheler Alpen, Wörthersee, Gasteinertal); selbstständig seit 2025. KI ist Werkzeug, nicht Kernidentität — die Tourismus-Erfahrung steht immer voran.

**Source of this system:** the design briefing document pasted by the user (July 2026), no attached codebase, Figma file, or logo assets. Everything here is built from that briefing; nothing was inferred from a screenshot or invented brand identity.

## Content fundamentals

- Voice: natürlich, menschlich, faktenbasiert — liest sich wie persönlich von Gernot geschrieben, nie wie KI-Text.
- LinkedIn: persönlich, punchy, leicht ironisch. Blog: professionell, SEO-strukturiert, empirisch fundiert.
- Emojis sparsam. Keine Trennlinien (─────). Keine langen Gedankenstriche — normaler Bindestrich.
- Jeder KI-unterstützte Content trägt einen Hinweis auf KI-Unterstützung. Feste Hashtags: **#GernotGoesAI**, **#GernotGoesKI**.
- "Angebot" statt "Auftragsbestätigung"; fortlaufende AO-Nummer.
- Kleinunternehmer-Steuerhinweis, wortwörtlich: "Gemäß § 6 Abs. 1 Z 27 UStG 1994 wird keine Umsatzsteuer berechnet."

## Visual foundations

- **Color:** Dunkelgrün `#0d6248` (Haupt), Orange `#f4a261` (Akzent), Taupe `#a29a88` (sekundär), Near-Black `#2b2b27` (Text/Kontrast), Off-White `#f4f7f4` (Hintergrund). Simplified 2-color CI: Orange + Near-Black only, for reduced-palette contexts. Max one accent (orange) per composition — it's a highlight color, not a second primary.
- **Type:** Archivo (display/headings, weight 600-800) + Open Sans (body — the fixed brand font for all Word documents, min. 12pt). See "Typography substitution" below.
- **Spacing:** 4px base unit, scale from 4 to 96px (`--space-1`…`--space-24`).
- **Radius:** modest, not startup-rounded — `--radius-sm` 6px (inputs/tags), `--radius-md` 10px (buttons), `--radius-lg` 16px (cards). Pill only for badges/switches.
- **Shadow:** soft and shallow (`--shadow-sm/md/lg`) — no hard drop shadows, no glow.
- **Cards:** white surface, 1px taupe-tinted border, soft shadow, generous padding (24px+). No colored left-border accent bars.
- **Backgrounds:** flat colors only — no gradients, no textures, no photography-heavy hero treatments documented. Off-white page background, white card surfaces.
- **Motion:** minimal — fast (120ms) hover/focus transitions, standard ease, subtle scale-down on button press. No bounce, no elaborate entrance animation.
- **Hover/press states:** hover = slightly darker fill (primary) or tinted background (ghost/secondary); press = 3% scale-down. Focus = orange focus ring.
- **Transparency/blur:** none observed — avoid glassmorphism/backdrop-blur; it doesn't match the grounded, practical brand tone.
- **Imagery:** no fixed photo style documented (see Iconography/open questions below) — ask before sourcing stock imagery.
- **Two documented sub-styles that must stay separate from the main CI:**
  - **ReviewRadar video/slide format** — dark CI slides alternating with light/green accent slides, logo present throughout.
  - **"Alpine Minimalism" (NotebookLM ReviewRadar report decks)** — Deep Teal `#1a4a4a`, Sage Green `#7a9e7e`, Sand `#f5f0e8`. A distinct secondary palette (`tokens/reviewradar-palette.css`), used only for those report presentations.

## Typography substitution — please review

No webfont files were supplied for Archivo/Open Sans (and no font was specified at all for web/social/decks — only Word documents specify Open Sans). This system currently loads **Archivo + Open Sans from Google Fonts** as the closest practical pairing: Open Sans continues the fixed document font for consistency; Archivo is a confident, grounded display companion. **Please confirm this pairing or supply real font files/licenses if the brand owns a different typeface for digital use.**

## Iconography

No icon set, icon font, or SVG sprite was supplied. No emoji usage pattern is documented outside "used sparingly" in written copy. No icon system is defined in this system yet — when a screen needs icons, substitute a neutral outline set (e.g. Lucide) and flag the substitution rather than hand-drawing icons.

## Logo

Two variants supplied: `assets/logo/masterdatei-website.png` (black background, use on dark surfaces) and `assets/logo/logo-hell-ohne-claim.png` (white background, use on light surfaces). Neither is transparent — always place with its own background, never try to knock one out.

## Imagery

`assets/imagery/weiter-blick.jpg` — real alpine landscape (Salzburger Land), warm daylight, wide green foreground. This sets the imagery direction: real alpine photography, not stock-generic mountains, paired with a dark-green gradient overlay (`.gr-hero-photo` in `components.css`) wherever text sits over a photo. Add more photos here as they're supplied.

## Components — intentional additions

No codebase or Figma file was attached, so this is a from-scratch component set sized to the brand's document/report/web needs: Button, IconButton, Input, Select, Checkbox, Radio, Switch, Card, Badge, Tag, Tabs, Dialog, Toast, Tooltip. None are literal replicas of an existing product UI — they're original, brand-consistent primitives.

## Index

- `styles.css` — root stylesheet, imports everything below.
- `tokens/` — `colors.css`, `typography.css`, `spacing.css`, `effects.css` (radius/shadow/motion), `fonts.css` (Google Fonts substitution, flagged above), `reviewradar-palette.css` (secondary, scoped).
- `components.css` — shared class-based styles for every component below.
- `components/forms/` — Button, IconButton, Input, Select, Checkbox, Radio, Switch.
- `components/display/` — Card, Badge, Tag.
- `components/navigation/` — Tabs.
- `components/feedback/` — Dialog, Toast, Tooltip.
- `guidelines/` — foundation specimen cards: colors (primary/simplified/semantic/ReviewRadar), type, spacing, radius/shadow, wordmark, hashtags.
- `templates/angebot-rechnung/` — branded Angebot/Rechnung A4 document template (logo slot, Leistungstabelle, tax note, bank footer).
- `templates/reviewradar-deck/` — "Alpine Minimalism" ReviewRadar report-deck sample slides.
- `thumbnail.html` — project tile.

## Open questions for the user

1. Confirm or replace the Archivo/Open Sans web substitution with real brand fonts.
2. Any icon system preference, or default to a neutral outline set (Lucide) going forward?
3. More alpine photography beyond `weiter-blick.jpg`, to build out the imagery library?
