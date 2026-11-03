# Handoff: Demo videos (admin "Démos / Demos" + homepage "02 — Démo / Demo")

## Overview
The admin publishes short product demos by pasting a **link** to a video hosted elsewhere (Google Drive now; YouTube and Vimeo later). Visitors watch them in a new **Demo** section of the public homepage. We store no video file.

Two parts, each in its existing visual world:
1. **Admin screen** inside the app — same shell, page header, table, dialog, fields, buttons and badges as the Clients page.
2. **Public section** on the homepage — same grid, type scale, eyebrows, section rhythm, light/dark tokens and Signal Lime as the homepage handoff.

## About the design files
`reference/` holds **HTML design references**, not production code. Recreate them in the codebase with its components, routing and theme system. Open any numbered file in a browser (keep every file in the folder together, including `support.js`). Each numbered file frames one state at its real size (1440 or 390) and scales it down to fit the window. The two source components are interactive:
- `Demos Admin.dc.html` — reorder, publish/hide, delete with confirmation, new/edit dialog with live link detection, counters and validation, FR/EN switch.
- `Homepage Demo Section.dc.html` — Play opens the lightbox; Esc, the close button or a click on the backdrop close it.

`exports/` holds a PNG of each reference: 1x for 1440, 2x for 390.

## Fidelity
**High-fidelity.** Final layout, type, colours, copy and states. Map colours to `tokens.css` (additions only; everything else comes from the homepage tokens).

## Recommendations
**Form → dialog, not side panel.** The app already creates and edits Clients in a centred dialog, so admins know the pattern. The task is short and focused (one link, one optional image, two short texts, two selects). A dialog keeps the list visible behind it as context. At 390px it becomes a near-full-height sheet with a scrolling body and a fixed footer, exactly like the Clients dialog. A side panel would add a second pattern for no gain.

**Languages → two tabs, not two columns.** In a 660px dialog, two columns would give each description textarea about 280px. That is too narrow for 300 characters, and the columns would collapse to tabs on mobile anyway. Tabs keep one layout at every width. Errors are never hidden: each tab shows its own status in words ("Complete" / "Missing", with an icon), and Save jumps to the first language with a missing field.

**Player → lightbox, not inline.** In a 3-column grid an inline player would be about 390px wide, too small for a product UI walkthrough. A lightbox gives a player up to 1080px wide on desktop and edge-to-edge on mobile, with one consistent behaviour. It follows the WAI-ARIA modal dialog pattern and returns focus to the card's Play button, so keyboard and screen-reader users don't lose their place.

---

## Part 1 — Admin "Démos / Demos"

### Shell (unchanged from Clients)
- Sidebar 248px, bg `--dx-surface`, right border `--dx-line`. New nav item **Démos / Demos** after Enquiries (icon: a play triangle inside a rectangle). Active item: bg `--dx-nav-active`, 600 weight, 4px `--dx-accent-text` bar on the left edge. Every item 40px high, radius 8px, 14px.
- Top bar 64px, bottom border. Breadcrumb: `DI XPERTIA /` (mono 11px .14em, `--dx-accent-text`) + page name (14px 600). On the right: FR/EN segmented control, bell, avatar.
- Content padding `clamp(24px,3vw,36px) clamp(16px,2.5vw,32px)`, vertical gap 24px.

### Page header
- H1 "Démos" / "Demos": 700 `clamp(32px,3vw,40px)`/1.05, -.025em.
- Intro: FR "Les vidéos affichées dans la section Démo du site web." / EN "The videos shown in the Demo section of the website." 15–17px, `--dx-muted`.
- Primary button "Nouvelle démo" / "New demo": 44px high, radius 8px, `--dx-btn-bg`/`--dx-btn-fg`, plus icon. Full width at 390px. Hidden in the empty state, where the call to action takes its place.

### List (desktop table)
Container: `--dx-card`, 1px `--dx-line-strong`, radius 12px. Under 940px of content width, it scrolls horizontally inside its container; under 760px of viewport, it becomes cards (see below). Header row: `--dx-head`, mono 11px .14em uppercase. Rows: 1px top border, cell padding 12px.

| Column | Content |
|---|---|
| ORDRE / ORDER (132px) | Drag handle (6 dots, `aria-hidden`, grab cursor), position `01` (mono 13px), **Move up** / **Move down** buttons 32×32 (1px border, radius 6px, arrow icon). First row: Move up `disabled` (opacity .35). Last row: Move down `disabled`. |
| APERÇU / PREVIEW (144px) | 120×68 16:9 thumbnail, radius 6px. With no preview image, an **AUTO** tag (mono 8px on ink) sits top-left so the admin knows the automatic thumbnail is in use. |
| TITRE / TITLE | Title in the **interface language** (14px 600), then the source on its own line (mono 11px muted: "Google Drive"). |
| SERVICE (150px) | Outlined pill (26px, radius 13px): Cloud / Cybersécurité · Cybersecurity / Logiciel sur mesure · Custom software. "—" when empty. |
| STATUT / STATUS (130px) | **Publiée / Published**: `--dx-ok-bg` fill, `--dx-ok-line` border, `--dx-ok-fg` text, check icon. **Masquée / Hidden**: dashed `--dx-line-strong` border, muted text, crossed-eye icon. The word is always present: never colour alone. |
| Actions (visually hidden header "Actions") | Text buttons, mono 12px with icon, 34px high: **Modifier / Edit** · **Masquer / Hide** or **Publier / Publish** (toggles right away, no dialog) · **Supprimer / Delete** (`--dx-danger`, opens the confirmation). |

Footer under the table: "4 démos · 3 sur le site" / "4 demos · 3 on the website" (14px muted).

**Reordering.** The arrows swap a row with its neighbour and save right away (optimistic update; roll back with a toast on failure). Focus stays on the arrow just pressed, which now belongs to the moved row's new position, so repeated presses keep moving the same demo. Announce the result in an `aria-live="polite"` region, e.g. "Sample — Restoring a cloud backup moved to position 2 of 4". Drag and drop is optional (the handle is drawn) and must call the same move endpoint.

Accessible names: every row button includes the title, e.g. "Move up: Sample — Restoring a cloud backup", "Monter : …", "Hide: …", "Delete: …". The table has a visually hidden `<caption>`: "Demos, in website display order".

### List at 390px (cards)
One card per demo: `--dx-card`, radius 12px, padding 12px. Top: 120×68 thumbnail + title (14px 600) + status badge and service pill (wrap). Bottom row under a divider: Move up / Move down (44×44), position (mono), then **Edit** and **Hide/Publish** as text buttons (44px high), and **Delete** as a 44×44 icon button named "Delete: {title}". Every touch target is ≥44px. No horizontal scroll.

### Empty state (first visit)
Dashed `--dx-line-strong` panel on `--dx-card`, radius 12px, centred. A 176×99 dark 16:9 panel with the lime play button, then:
- H2 "Aucune démo pour l'instant" / "No demos yet" (600 20–24px)
- FR "Collez le lien d'une vidéo hébergée sur Google Drive pour ajouter votre première démo. Une fois publiée, elle apparaît dans la section Démo du site." / EN "Paste a link to a video hosted on Google Drive to add your first demo. Once published, it appears in the Demo section of the website."
- Button "Ajouter la première démo" / "Add the first demo" (opens the dialog)
- Note (mono 11px): FR "La section Démo reste absente du site tant qu'aucune démo n'est publiée." / EN "The Demo section stays off the website until a demo is published."

### Add / Edit dialog
`role="dialog"`, `aria-modal="true"`, labelled by its title. Max width 660px, radius 14px, `--dx-card`, shadow `0 30px 80px -20px rgba(0,0,0,.45)`, backdrop `--dx-scrim`. Header (title 18px 700 + 40px close button), scrolling body (padding 22px 24px 26px, gap 24px), fixed footer. Labels follow the app: mono 11px 600 .14em uppercase, with "Facultatif / Optional" in mono 400 muted. Inputs 44px, radius 8px, 1px `--dx-line-strong`, `--dx-input`. Error border and text use `--dx-danger`, with `aria-invalid` and `aria-describedby`. Title: "Nouvelle démo" / "New demo", or "Modifier la démo" / "Edit demo". Focus moves to the first field on open, Tab is trapped inside the dialog, Esc closes (except while saving), and focus returns to the button that opened it.

**1. Lien de la vidéo / Video link** (`type="url"`, mono 13px)
- Helper: FR "Collez le lien de partage d'une vidéo Google Drive. Les liens YouTube et Vimeo seront reconnus plus tard." / EN "Paste the share link of a Google Drive video. YouTube and Vimeo links will be recognised later."
- **Source chip** inside the input on the right once recognised: pill on `--dx-head`, mono 11px, a 7px square in the source colour (Drive #1FA463, YouTube #E5484D, Vimeo #1AB7EA) + the name in words. Detection patterns: Drive `drive.google.com/file/d/{id}` or `open?id={id}`; YouTube `youtube.com/watch?v=` or `youtu.be/`; Vimeo `vimeo.com/{digits}`. While YouTube/Vimeo are not enabled, show their chip with the error "Not supported yet".
- **Unrecognised** (shown as soon as the field holds text): FR "Lien non reconnu. Collez un lien de partage Google Drive (drive.google.com/file/d/…)." / EN "We don't recognise this link. Paste a Google Drive share link (drive.google.com/file/d/…)."
- **Drive file not public** (checked by the server on blur and again on save, since the browser can't tell): FR "Ce fichier Drive n'est pas partagé publiquement. Dans Drive, réglez l'accès général sur « Tous les utilisateurs disposant du lien », puis enregistrez à nouveau." / EN "This Drive file isn't shared publicly. In Drive, set General access to "Anyone with the link", then save again."
- **In-app preview**, once the link is valid: a panel on `--dx-bg` with a 220px 16:9 embed (`https://drive.google.com/file/d/{id}/preview`) next to "Est-ce la bonne vidéo ? / Is this the right video?" and FR "Aperçu visible par vous seul — les visiteurs voient notre propre carte jusqu'à ce qu'ils lancent la lecture." / EN "Preview for you only — visitors see our own card until they press Play." The reference shows a placeholder where the iframe goes. At 390px the preview stacks above the text.

**2. Lien de l'image d'aperçu / Preview image link** — optional
- Filled: a 96×54 thumbnail of the image next to the input. If the image fails to load, show the error "Image not found at this link."
- Empty: info icon + **"La miniature automatique de la vidéo sera utilisée." / "The video's automatic thumbnail will be used."** followed by (muted) "Sa qualité n'est pas garantie ; une image 1280 × 720 donne le meilleur rendu." / "Its quality isn't guaranteed; a 1280 × 720 image looks best."

**3. Contenu / Content** — tabs (WAI-ARIA tabs: ←/→, Home/End, roving tabindex)
- Two equal tabs on a `--dx-bg` track: `FR Français`, `EN English`. The active tab is raised on `--dx-card`. Each tab shows its status on the right: ✓ "Complet / Complete" (muted) or ⚠ "Manquant / Missing" (`--dx-danger`).
- The panel carries `lang="fr"` or `lang="en"`. **Titre · FR / Title · FR** (max 80) and **Description · FR** (textarea, 4 rows, max 300), each with a live counter "40 / 80" (mono 11px, `aria-live="polite"`). Inputs enforce `maxLength`.
- Hint: FR "Les deux langues sont obligatoires : le site affiche à chaque visiteur sa langue." / EN "Both languages are required: the website shows each visitor their language."
- Missing on save: FR "Ajoutez le titre en anglais." / "Ajoutez la description en anglais." · EN "Add the English title." / "Add the English description." Save switches to the first incomplete tab.

**4. Service** — native select, optional: Aucun service / No service, Cloud, Cybersécurité / Cybersecurity, Logiciel sur mesure / Custom software.

**5. Statut / Status** — two radio cards (44px): Publiée / Published (default) and Masquée / Hidden. The selected card gets a `--dx-fg` border. Hint: FR "Les démos masquées ne sont pas affichées sur le site." / EN "Hidden demos are not shown on the website."

**Display order** isn't in the form: a new demo goes to the end of the list and moves with the arrows.

**6. Footer** — "Annuler / Cancel" (outlined) and "Enregistrer / Save" (primary).
- **Validation error**: an alert box at the top of the body (`role="alert"`, danger border): FR "3 champs demandent votre attention avant l'enregistrement." / EN "3 fields need attention before saving." Each field shows its inline error too.
- **Saving**: the Save button shows a 14px spinner and "Enregistrement… / Saving…" with `aria-disabled`. Cancel is disabled and Esc is ignored.
- **Server error**: an alert above the buttons: FR "Impossible d'enregistrer la démo. Vérifiez votre connexion et réessayez — rien n'est perdu." / EN "Couldn't save the demo. Check your connection and try again — nothing was lost." The form stays filled.
- **Success**: the dialog closes and a toast appears (bottom-right, `role="status"`, lime tint as on Clients): "Démo « … » enregistrée." / "Demo "…" saved."

### Delete confirmation
`role="alertdialog"`, max width 440px. Title "Supprimer cette démo ?" / "Delete this demo?". Body: FR "Elle disparaît du site web. La vidéo elle-même reste sur Drive." / EN "It disappears from the website. The video itself stays on Drive." The demo title appears in a `--dx-bg` box. Buttons: Annuler / Cancel (**gets initial focus**) and Supprimer / Delete (`--dx-danger-bg`, trash icon). After deleting, a toast "Démo supprimée. / Demo deleted." appears and focus moves to the next row's Edit button (or to "New demo" if the list is now empty).

---

## Part 2 — Homepage "02 — Démo / Demo"

### Placement and numbering
Insert the section **after Services**. Renumber: Services 01 · **Demo 02** · Engagement **03** · About **04**. Header nav: Home / Services / **Demo** / About / Contact (FR: Accueil / Services / **Démo** / À propos / Contact), with Demo linking to `#demo`.

**When no demo is published, the section is not rendered at all**: no heading, no empty state, no nav item, and Engagement / About keep the numbers 02 / 03. The server decides this before the page renders.

### Layout
- `<section id="demo" aria-labelledby="demo-title">`, bg `--dx-bg`, top border `rgba(fg,.1)`, padding `clamp(72px,9vw,128px)` (same as Services). Container 1312px + gutter.
- Header row, as on Services: eyebrow (mono 12px 600 .18em, `--dx-accent-text`) + H2 on the left; note on the right (15px/1.6, muted .68, max 40ch). Wraps under 860px.
- Rule `1px solid fg`, then the grid: `repeat(auto-fill, minmax(min(100%,340px),1fr))`, gap `clamp(28px,3vw,40px) clamp(20px,2vw,28px)`, padding-top `clamp(24px,3vw,36px)`. That gives 3 columns at 1440 and 1 at 390. For 1–6 demos, rows fill left to right; a single demo takes one column and the rest stays empty (intentional: same rhythm as Services).

### Copy
- Eyebrow: "02 — Démo" / "02 — Demo"
- H2: FR "Voir en action" / EN "See it in action"
- Note: FR "De courtes démonstrations de ce que nous concevons et exploitons. Chaque vidéo se charge depuis son hébergeur seulement quand vous lancez la lecture." / EN "Short walkthroughs of what we build and run. Each video loads from its host only when you press play."

### Card
- `<article>`. The whole 16:9 preview is one `<button>` with `aria-label="Play: {title}"` / "Lire : {title}" and `aria-haspopup="dialog"`, radius 12px. Hover: ring `0 0 0 1px fg` + soft shadow.
- Preview image: `object-fit: cover`, `loading="lazy"`, empty `alt` (the button already names the video). Served **from our own domain or CDN**: the automatic thumbnail must be fetched and cached server-side when the demo is saved, so the page never requests images from Google, YouTube or Vimeo before Play.
- Play button: 60px circle, `--dx-signal` fill, ink triangle, inset 1px `rgba(16,19,20,.14)`, positioned 18px from the bottom-left. Lime is used only as a fill, never as text on a light background.
- Under the preview (gap 18px): service tag (mono 11px .14em uppercase, `--dx-accent-text`; omitted when there is no service) · title H3 600 `clamp(20px,1.7vw,24px)`/1.22 · description 15px/1.6 muted .72, clamped to **3 lines** (`-webkit-line-clamp: 3`).
- Sample content in the references is labelled "Sample —" / "Exemple —", and the placeholder previews read "SAMPLE PREVIEW · 0n". Replace both with real data.

### Playing (lightbox)
- Overlay `rgba(10,12,13,.84)`, padding 48px desktop / 12px mobile. `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the title. Panel `#1A1F21` (dark in both themes), border `rgba(243,242,238,.08)`, radius 16px, max width 1080px.
- Header: service tag (lime on dark is fine) + title (600 18–24px, paper) + a 44px circular close button `aria-label="Close video"` / "Fermer la vidéo".
- Player: 16:9, radius 10px, `<iframe src="https://drive.google.com/file/d/{id}/preview" title="Video: {title}" allow="autoplay; fullscreen" allowfullscreen>`. **The iframe is created only when Play is pressed and destroyed on close.** Nothing is sent to Google, YouTube or Vimeo before that click.
- Caption under the player (mono 12px, paper .72): "Lecture via Google Drive" / "Played via Google Drive" (YouTube / Vimeo later). On desktop, "Échap pour fermer / Esc to close" on the right (`aria-hidden`).
- Behaviour: focus moves to the close button on open, Tab is trapped (close button ↔ iframe), and **Esc**, the close button or a click on the backdrop close it. On close, **focus returns to the card's Play button**. Page scroll is locked while open (`overflow:hidden` on `<html>`).

### States
- **Loading**: 3 skeleton cards with the same geometry (16:9 block radius 12px + 4 bars) in `rgba(fg,.07–.10)`. Opacity pulses 1 ↔ .45 over 900ms, staggered by 120ms. The grid has `aria-busy="true"` and a visually hidden status "Chargement des démos… / Loading demos…". Prefer server rendering so this state stays rare.
- **Preview image fails to load** (`onerror`): replace it with the branded fallback, the logo mark (56×41) centred on `--dx-surface` with a 1px `rgba(fg,.12)` border and "DI XPERTIA · DEMO" (mono 10px) under it. The content sits in the upper 80% so the Play button never covers it. Shown on card 3 in `14 Public section - light EN 390`.
- **No published demo**: the section is not rendered (see above).

### Responsive
At 1440: 3 columns. At 390: 1 column, nav hidden (logo + Dashboard button remain, per the homepage breakpoint at 860px), H2 wraps, lightbox edge to edge with 12px margins. No horizontal scroll at any width.

---

## Accessibility
- **Contrast (WCAG AA)**: body and muted text ≥4.5:1 in both themes. `--dx-accent-text` is olive #5C7A0A on paper and lime only on dark. Status colours: see `tokens.css`. Lime is only ever a fill.
- **Keyboard**: everything is reachable in DOM order. Focus is visible everywhere (`:focus-visible` → 2px `--dx-focus-outline` + 5–6px lime ring, as on the homepage). Reordering works without drag. The tabs use the arrow-key pattern.
- **Names**: Play buttons "Play: {title}" / "Lire : {title}"; row actions include the title; the close button is labelled; icons are `aria-hidden`.
- **Dialogs**: WAI-ARIA dialog pattern for the form, the delete confirmation (`alertdialog`, focus on Cancel) and the lightbox (initial focus, trapped Tab, Esc, focus returned to the opener).
- **Status never by colour alone**: badges always carry the word and an icon; tab status is in words; error fields have text messages, a red border and `aria-invalid`.
- **Live regions**: character counters, the reorder result, toasts (`role="status"`), validation and server errors (`role="alert"`).
- **Motion**: under `prefers-reduced-motion: reduce`, turn off every animation and transition (skeleton pulse, hover lifts, spinner rotation; show "Saving…" text only, and no lightbox fade).

## Data and API notes
- `Demo { id, videoUrl, source: 'drive'|'youtube'|'vimeo', videoId, previewImageUrl?, cachedThumbnailUrl, titleFr (≤80), titleEn (≤80), descriptionFr (≤300), descriptionEn (≤300), service?: 'cloud'|'security'|'software', position (int), status: 'published'|'hidden' }`.
- Validate on the server: recognised source, Drive file publicly viewable, both languages present, length limits.
- Public endpoint: published demos only, ordered by `position`, with the language resolved server-side; omit the section when the list is empty.
- `PATCH /demos/{id}/position` (move ±1) and `PATCH /demos/{id}/status`, both admin-only.

## Files
- `README.md` — this spec
- `tokens.css` — added tokens only, mapped to the existing ones
- `reference/` — `Demos Admin.dc.html` and `Homepage Demo Section.dc.html` (interactive sources) + `support.js` + numbered state files:
  01 admin list light FR · 02 admin list dark EN · 03 empty state · 04 form empty · 05 form filled (FR) · 06 form errors (dark EN) · 07 saving · 08 save failed · 09 delete confirm · 10 admin 390 list · 11 admin 390 dialog (dark) · 12 public light EN 1440 · 13 public dark FR 1440 · 14 public light EN 390 (with the image fallback) · 15 public dark FR 390 · 16 player open 1440 · 17 player open dark 390 · 18 loading
- `exports/` — one PNG per numbered reference
