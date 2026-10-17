# Prompt to paste into Claude Code

Place the `design_handoff_homepage/` folder at the root of your repository, then paste:

---

I'm handing you a homepage redesign for DI Xpertia. Everything is in `design_handoff_homepage/`:
- `README.md` — full spec (layout, exact copy, colours, type, interactions, accessibility)
- `tokens.css` — light/dark theme tokens
- `TICKETS.md` — backlog HP-01 → HP-11
- `reference/` — HTML design references (open in a browser to see the motion; they are references, NOT code to copy)

Instructions:
1. First read the README, the tickets and the references, then explore our codebase: framework, routing, styling approach, existing theme switch (light/dark), components and the current homepage. Summarise what you found and propose an implementation plan mapped to the tickets, including which existing components/tokens you will reuse. Wait for my approval before writing code.
2. Recreate the design in our stack using our existing patterns — do not paste the reference HTML, inline styles or `support.js` into the app.
3. Implement one ticket at a time, in order, each as a separate commit (or PR) titled `HP-xx: …`. After each ticket, tell me what changed and how to check it.
4. Hard requirements: both themes driven by our existing theme switch; every animation disabled under `prefers-reduced-motion`; animate transform/opacity only; WCAG AA contrast; visible keyboard focus; accessible tabs (WAI-ARIA); mobile-first, verified at 390px and 1440px; no new heavy dependencies; keep the "Go to Dashboard" button pointing to our existing dashboard route.
5. Do not invent content: no fake logos, figures, testimonials or phone numbers. If a link target or piece of content doesn't exist in our app, ask me instead of guessing (see README › Open questions).
6. At the end, run HP-11 (QA) and give me a checklist with results.

---
