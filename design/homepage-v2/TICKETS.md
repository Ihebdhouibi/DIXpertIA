# Homepage redesign — tickets

Order = recommended implementation order. Each ticket is one PR. Reference: README.md + `reference/*.dc.html`.

---

### HP-01 · Theme tokens (light + dark)
Add the tokens from `tokens.css` to the codebase's theme system (CSS vars, Tailwind theme or equivalent) wired to the existing theme switch, fallback `prefers-color-scheme`.
**Done when:** toggling the platform theme switches all homepage colours with no reload; no hard-coded hex values in homepage components.

### HP-02 · Fonts & type scale
Load Space Grotesk (400–700) and JetBrains Mono (400–600) with `font-display: swap` (preload the 700 weight). Add the type styles from README › Type scale.
**Done when:** H1/H2/eyebrow/body match the reference at 390px and 1440px.

### HP-03 · Motion foundation & accessibility utilities
Shared hook/util: `useReducedMotion`, `useInView` (IntersectionObserver, threshold .12, once) and a `<Reveal index>` wrapper (800ms, 22px rise, 90ms stagger). Global `:focus-visible` style. Global reduced-motion kill switch.
**Done when:** reduced-motion on the OS → no element moves anywhere on the page; keyboard focus is visible on every interactive element in both themes.

### HP-04 · Header
Sticky 68px blurred header: logo, nav (hidden < 860px), **Go to Dashboard** linked to the existing dashboard route.
**Done when:** matches reference in both themes; Home has `aria-current`; no layout shift on scroll.

### HP-05 · Hero — grid, typed headline, rule, CTAs
Grid background + vignette, meta row, typed H1 with lime cursor (reserved width, `aria-label`), drawing rule, lead text, two buttons.
**Done when:** no reflow during typing (CLS ≈ 0); screen reader reads the full headline once; reduced-motion shows full headline immediately.

### HP-06 · Hero — ops console
Dark panel with live clock, 3 progress rows, log loop (README › Interactions). `role="img"` + label. Timers cleaned up on unmount; pause when tab hidden (`visibilitychange`).
**Done when:** loop matches reference timing; reduced-motion shows the finished static state; dark panel identical in both themes.
**Blocked by decision:** keep "ops / live" or rename "how we work" (README › Open questions #1).

### HP-07 · Services list
Indexed row list (01–03), whole row is a link, hover surface + cursor spotlight, reveal stagger.
**Done when:** spotlight follows pointer (disabled on touch/reduced-motion); rows reflow cleanly at 390px.

### HP-08 · Engagement tabs ("Ways to work with us")
Accessible tabs (WAI-ARIA pattern: arrows/Home/End, roving tabindex), panel with checklist + "Best for", phase diagram with animated bars. Copy from README.
**Done when:** passes keyboard-only test; labels inside bars meet AA (ink on lime, paper on empty); active tab = ink pill (light) / lime pill (dark).

### HP-09 · About / CTA + magnetic button
Dark grid section, copy, magnetic button with lime glow pulse.
**Done when:** magnet only on fine pointers (`(hover:hover) and (pointer:fine)`), disabled under reduced-motion; button stays fully clickable/focusable.

### HP-10 · Footer
4-column responsive footer, "© 2026 DI Xpertia SUARL".
**Done when:** only links to existing pages are shown (see Open question #2); legal name reads SUARL.

### HP-11 · QA — responsive, a11y, performance
- Visual check vs reference at 390, 768, 1440px in light and dark.
- axe / Lighthouse a11y ≥ 95, all text ≥ 4.5:1 (3:1 headlines).
- Lighthouse performance ≥ 90 mobile; animations use transform/opacity only; no new heavy dependency.
- Reduced-motion and keyboard-only passes.
**Done when:** all checks recorded in the PR description with screenshots of both themes.
