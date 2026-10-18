# Handoff: DI Xpertia public homepage (light + dark)

## Overview
Redesign of the public homepage of DI Xpertia (IT services: cloud infrastructure, cybersecurity, custom software). Tagline: "Digital intelligence, expertly engineered." Goal: a page that feels alive and engineered — two signature moments (typed headline with terminal cursor, live ops console) — while staying premium and restrained. Must ship in **both light and dark themes**, matching the platform's existing theme switch.

## About the design files
Files in `reference/` are **design references built in HTML** — prototypes showing intended look and behaviour, **not production code to copy**. Recreate them in the target codebase using its existing framework, component patterns, routing and theme system. Open them in a browser (keep `support.js` next to them) to see live behaviour.

## Fidelity
**High-fidelity.** Final colours, typography, spacing, copy and motion. Recreate pixel-accurately; map values to `tokens.css` (or the codebase's existing tokens if equivalent ones exist).

## Global layout
- Container: `max-width: 1312px; margin: 0 auto; padding-inline: clamp(20px,5vw,48px)`.
- Fonts: Space Grotesk 400/500/600/700, JetBrains Mono 400/500/600 (Google Fonts or self-hosted).
- Section rhythm: vertical padding `clamp(72px,9vw,128px)` (services), `clamp(72px,9vw,120px)` (engagement), `clamp(80px,10vw,136px)` (CTA).
- Breakpoint: primary nav hidden below **860px** (logo + Dashboard button remain). Everything else reflows via `auto-fit/minmax` grids and flex-wrap. Must be verified at **390px** and **1440px**.
- Section dividers: `1px solid rgba(fg,.1)`.

## Type scale
| Role | Font | Size / line-height | Weight | Tracking |
|---|---|---|---|---|
| H1 hero | Space Grotesk | clamp(48px,8.6vw,136px) / .95 | 700 | -.045em, max-width 14ch, text-wrap: balance |
| H2 section | Space Grotesk | clamp(32px,3.6vw,52px) / 1.05 | 700 | -.025em |
| H2 CTA | Space Grotesk | clamp(34px,4.4vw,64px) / 1.04 | 700 | -.03em, max 16ch |
| H3 engagement | Space Grotesk | clamp(26px,2.6vw,36px) / 1.15 | 600 | -.02em |
| Service title | Space Grotesk | clamp(24px,2.6vw,36px) / 1.1 | 600 | -.02em |
| Lead body | Space Grotesk | clamp(16px,1.4vw,19px) / 1.6 | 400 | — muted .72 |
| Body | Space Grotesk | 15–17px / 1.6 | 400 | muted .68–.72 |
| Eyebrow | JetBrains Mono | 12px / 1, uppercase | 600 | .18em, accent-text colour |
| Meta / tags | JetBrains Mono | 11px / 1.4, uppercase | 500 | .14–.18em, muted .6 |
| Console | JetBrains Mono | 11–12px | 400–500 | .12–.14em on labels |

## Sections

### 1. Header (sticky)
- Height 68px, `position: sticky; top:0; z-index:30`, background `--dx-header-bg` + `backdrop-filter: blur(12px)`, bottom border `rgba(fg,.1)`.
- Left: logo mark (inline SVG, see Assets) 30×22 + wordmark "DI" (Space Grotesk 700 19px, -.02em) + "Xpertia" (JetBrains Mono 500 18px, -.03em, `--dx-accent-text`).
- Centre (≥860px): nav Home / Services / About / Contact — 14px 500, gap 32px, inactive `rgba(fg,.66)`, hover/current `fg`. Home has `aria-current="page"`.
- Right: **"Go to Dashboard"** (keep — links to the existing dashboard route). 40px high, padding 0 18px, radius 8px, 14px 600, bg `--dx-btn-strong-bg`, text `--dx-btn-strong-fg`, hover `--dx-btn-strong-hover`.

### 2. Hero
- Background `--dx-bg` with a 48px engineering grid: two `linear-gradient`s of `--dx-grid-line` 1px, `background-size:48px 48px`, plus a radial vignette `radial-gradient(ellipse 80% 70% at 30% 40%, transparent 40%, var(--dx-bg) 100%)` on top.
- Padding `clamp(56px,8vw,112px)` top / `clamp(56px,7vw,96px)` bottom; vertical gap `clamp(32px,4vw,56px)`.
- Meta row (flex, space-between, wrap): "Cloud · Cybersecurity · Custom software" and "36.45° N  10.73° E — Nabeul" (mono 11px, .18em, muted .62).
- **H1 typed headline** — see Interactions. Cursor block: `.38em × .68em`, radius .05em, colour `--dx-accent-text`.
- 1px rule in `fg`, draws in from the left.
- Two-column grid `repeat(auto-fit,minmax(min(100%,420px),1fr))`, gap `clamp(32px,5vw,72px)`:
  - Left: lead paragraph (max 48ch) — "We design, build and run the systems your organisation depends on — cloud infrastructure, security and software, engineered for reliability from the first line." Then buttons (gap 12px):
    - Primary "Contact us →": 52px high, padding 0 24px, radius 10px, bg `--dx-signal`, text `--dx-on-signal`, 15px 600, inset 1px `rgba(16,19,20,.14)`; hover bg `--dx-signal-hover` + translateY(-1px).
    - Secondary "Our services": same size, 1px border `rgba(fg,.3)`, transparent/bg; hover border `fg`.
  - Right: **Ops console** (always dark): bg `--dx-panel`, border `--dx-panel-border`, radius 16px, padding 20px 22px 22px, shadow `0 30px 60px -30px rgba(16,19,20,.5)` (dark: `rgba(0,0,0,.7)`). `role="img"`, `aria-label="Illustrative operations console"`.
    - Top row: mark + "ops / live" — and live clock HH:MM:SS (visitor's local time). Mono 11px .14em, paper .6. ⚠ See Open questions about the "live" label.
    - 3 rows grid `92px minmax(0,1fr) 96px`, gap 14px: label (CLOUD / SECURITY / SOFTWARE), 4px progress track `rgba(paper,.12)` with lime fill (scaleX), status right-aligned.
    - Log block (top border `rgba(paper,.1)`, min-height 104px): last 4 lines of: "› plan infrastructure", "› provision network … ok", "› harden access policies … ok", "› run test suite … ok", "› deploy release … ok", "› monitor · all systems nominal".

### 3. Services — "01 — Services / What we do"
- Header row: eyebrow + H2 left; right note (max 38ch): "Three disciplines, one team — so the cloud, the security and the code are designed together."
- List with top border 1px `fg`. Each row is a link (whole row clickable), flex-wrap, padding `clamp(24px,3vw,36px) clamp(4px,1.5vw,20px)`, bottom border `rgba(fg,.16)`:
  - Number (mono 14px, accent-text) · Title + tags · Description (16px, muted .72) · 48px circular arrow (1px border `rgba(fg,.25)`).
  - Rows: 01 Cloud Infrastructure — "Architecture · Migration · Operations" — "Scalable, secure cloud architecture designed for high availability and enterprise performance." / 02 Cybersecurity — "Audit · Hardening · Compliance" — "Threat protection and compliance management that keeps your critical data assets safe." / 03 Custom Software — "Web · Mobile · Integrations" — "Bespoke applications built around your operational workflows — not the other way round."
  - Hover: background `--dx-surface` + cursor spotlight `radial-gradient(420px circle at var(--mx) var(--my), var(--dx-spotlight), transparent 65%)`.

### 4. Engagement — "02 — Engagement / Ways to work with us"
- Section bg `--dx-surface`, top & bottom borders.
- Right note: "Choose how involved you want to be. We adapt the model, not the standard."
- **Tabs** (WAI-ARIA tabs pattern): container `role="tablist"`, grid `repeat(auto-fit,minmax(min(100%,220px),1fr))`, gap 8px, padding 6px, radius 14px, bg `--dx-bg`, 1px border `rgba(fg,.1)`. Each tab: min-height 56px, padding 12px 18px, radius 10px, 16px 600, mono number 12px before label. Active: bg `--dx-tab-active-bg`, text `--dx-tab-active-fg`, number `--dx-tab-active-num`. Inactive: transparent, text `fg`, number `--dx-accent-text`.
- **Panel** (`role="tabpanel"`), grid `repeat(auto-fit,minmax(min(100%,420px),1fr))`:
  - Left: H3 headline, description (17px, max 52ch), checklist (rows 14px vertical padding, bottom borders `rgba(fg,.1)`, 6×10 accent block bullet), "BEST FOR →" line (mono 12px).
  - Right: **"Who leads each phase"** diagram (always dark panel, radius 16px, padding 24px). Legend: lime square = DI Xpertia, outlined square = Your team. 4 rows (SCOPE, BUILD, LAUNCH, RUN): label column 96px + 28px bar (1px border `rgba(paper,.22)`, radius 6px), lime fill scaleX 0 / .5 / 1 = your team / joint / DI Xpertia. Label inside the bar ("DI Xpertia" / "joint" / "your team"): **ink `#101314` whenever fill > 0, paper otherwise** (contrast). Footnote under a divider.
- Content (exact copy):
  - **01 Project delivery** — "You define the outcome. We deliver it, end to end." — "A fixed scope, a dedicated team and a clear timeline. We handle architecture, build, security and launch, then hand over a documented system you fully own." — Items: Scoping workshop and written specification · Dedicated team with a single technical lead · Security reviewed before every release · Full documentation and handover — the code is yours — Best for: "A new platform, a migration or a well-defined product." — Phases: Scope joint, Build DI Xpertia, Launch DI Xpertia, Run your team — Footnote: "We lead delivery; you validate at each milestone."
  - **02 Team extension** — "Senior engineers, embedded in your team." — "Your roadmap, your rituals, your tools. Our engineers join your team to add capacity or expertise you don't have in-house — cloud, security or software." — Items: Engineers matched to your stack and seniority needs · Work inside your tools, sprints and code review · Knowledge transfer built into the engagement · Scale up or down as your roadmap changes — Best for: "Teams that need to move faster without hiring." — Phases: Scope your team, Build joint, Launch joint, Run your team — Footnote: "You lead the roadmap; we strengthen execution."
  - **03 Managed operations** — "We run it, so your team can build." — "Ongoing operation of your cloud and applications: monitoring, updates, security patches and incident response, with regular reporting on what we did and why." — Items: Monitoring and alerting across your systems · Security patching and access reviews · Incident response and post-incident reports · Regular reviews of cost, risk and performance — Best for: "Systems that must stay up, secure and up to date." — Phases: Scope joint, Build joint, Launch DI Xpertia, Run DI Xpertia — Footnote: "We run day to day; you keep full visibility and control."

### 5. About / CTA — "03 — About"
- Bg `--dx-cta-bg` (always dark; in dark theme #171B1C + top border `rgba(paper,.08)`), same 48px grid in `rgba(243,242,238,.045)`.
- Grid `repeat(auto-fit,minmax(min(100%,460px),1fr))`, gap 40px. Left: eyebrow (lime), H2 "Ready to transform your IT infrastructure?", body "Partner with DI Xpertia to bring modern, reliable technology to your organisation." (paper .74).
- Right: **magnetic button** "Get started today →" — 60px high, padding 0 32px, radius 12px, lime bg, ink text, 17px 600. Sits in a hit zone with padding 56px 72px; behind it a lime glow (280×100, radius 50%, `filter: blur(42px)`, opacity .28).

### 6. Footer
- Bg `--dx-bg`. Grid `repeat(auto-fit,minmax(min(100%,200px),1fr))`, gap 40px 32px, padding 56px gutter 40px.
- Col 1: logo + "DIGITAL INTELLIGENCE, / EXPERTLY ENGINEERED" (mono 11px .16em, muted .66).
- Company: About us, Leadership, Careers · Links: Services, Case studies, Go to Dashboard · Contact: Support, Sales, "Rue de Pasteur, Dar Chaabane El Fehri, 8011 Nabeul, Tunisia".
- Bottom bar: "© 2026 DI Xpertia SUARL. All rights reserved." (13px, muted .62) — note **SUARL**, not SAS.

## Interactions & behaviour
| Element | Behaviour | Timing |
|---|---|---|
| H1 typing | Cursor blinks alone, then headline types char by char; full text width reserved from the start (untyped remainder rendered `color: transparent`) so nothing reflows. `aria-label` on H1 holds the full sentence; visual spans `aria-hidden`. | start 900ms, 44ms/char, blink 1050ms hard on/off (steps) |
| Cursor | Solid while typing, blinks before and after. | 1050ms infinite |
| Hero rule | scaleX 0→1 from left. | 1400ms, delay 300ms, `--dx-ease-draw` |
| Scroll reveal | Elements fade + rise 22px when 12% visible, once. Stagger by index. | 800ms, 90ms step, `--dx-ease-out` |
| Ops console | Tick every 1100ms, 10-tick loop. Row i progress = clamp((tick − 2i)/2, 0, 1). Status: "○ queued" → "○ provisioning/scanning/building" → "● healthy/protected/shipped" (lime when done). Log reveals one line per tick, shows last 4. Bars animate scaleX. | bars .9s `--dx-ease-out` |
| Service spotlight | pointermove sets `--mx/--my` on the row; leave resets off-screen. | — |
| Tabs | Click or keyboard: ←/→/↑/↓ cycle, Home/End jump; roving `tabindex` (active 0, others −1); `aria-selected`, `aria-controls`, panel `aria-labelledby`. Panel fades in (opacity 0→1, translateY 10px→0). Phase bars animate scaleX. | panel 450ms, bars .7s |
| Magnetic CTA | Button follows the pointer within its hit zone: translate x·30px, y·22px (x,y ∈ [−.5,.5]); resets on leave. | .45s `--dx-ease-magnet` |
| CTA glow | Pulse opacity .2↔.36, scale .92↔1.08. | 2800ms alternate infinite |
| Focus | `:focus-visible` → 2px outline `--dx-focus-outline`, offset 3px, plus 6px ring `--dx-focus-ring`, radius 8px. | — |

**Performance:** animate only `transform` and `opacity` (the spotlight uses a CSS variable on background — acceptable, pointer-driven). No video, no 3D, no animation library required.

**prefers-reduced-motion: reduce** → disable every animation & transition: headline shown complete immediately, console shown static in its finished state, no reveal (content visible), no magnet, no glow pulse, no panel fade, smooth scroll off.

## Theming
- Single implementation, two themes via `tokens.css` (`[data-theme="dark"]` overrides). Hook it to the platform's existing theme switch / stored preference; fall back to `prefers-color-scheme`.
- The ops console, phase diagram and CTA are **dark in both themes**.
- Lime is never used for small text on paper (fails AA) — use `--dx-accent-text` (#5C7A0A in light, lime in dark).

## State
- `typedCount` (int), `consoleTick` (0–9), `clock` (Date, 1s), `activeTab` (0–2), `isWide` (≥860px — prefer a CSS media query), `reducedMotion` (media query). Clear all timers/observers on unmount. No data fetching.

## Assets
- Logo mark (inline SVG, viewBox `12 18 38 28`): `<path d="M17 23 L27 32 L17 41" fill="none" stroke="{fg}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/><rect x="34" y="22" width="13" height="20" rx="1.5" fill="{accent}"/>` — stroke `fg`, block `--dx-accent-text` (lime on dark backgrounds).
- `assets/DIXpertia-favicon.svg`.
- No photos, client logos, figures or phone numbers — intentionally (no fake content).

## Open questions for the product owner
1. Console label "ops / live" + clock may read as real telemetry. Option: rename to "how we work".
2. Footer links Leadership / Careers / Case studies — only keep if real pages exist.
3. Real routes for "Go to Dashboard", "Contact us", "Get started today", service rows.

## Files
- `reference/Homepage - Light.dc.html` — light theme reference
- `reference/Homepage - Dark.dc.html` — dark theme reference
- `reference/support.js` — runtime needed to open the references locally
- `tokens.css` — light/dark token map
- `TICKETS.md` — implementation backlog
- `PROMPT.md` — prompt to paste into Claude Code
