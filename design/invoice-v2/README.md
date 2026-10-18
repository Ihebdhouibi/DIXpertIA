# DI Xpertia — Invoice (Facture) · Design handoff

Target: server-side PDF generated with **ReportLab (Python)**. Everything below is in **mm** or **pt** (1 pt = 0.3528 mm, 1 mm = 2.835 pt). Origins are given from the **top-left of the content box** unless stated; ReportLab's origin is bottom-left, so convert with `y_rl = 297mm − 15mm − y`.

The HTML files in `reference/` are for **reading only** — rebuild the layout in the generator; do not port the HTML/CSS.

```
design_handoff_invoice/
├── README.md          ← this spec
├── reference/         ← open any *.dc.html in a browser (keep support.js + assets/ next to them)
│   ├── 01 FR issued.dc.html
│   ├── 02 EN issued.dc.html
│   ├── 03 Draft.dc.html
│   ├── 04 Two-page.dc.html
│   ├── Facture DI Xpertia.dc.html   (source all four load; also has the client-abroad page + spec)
│   ├── support.js
│   └── assets/dixpertia-lockup.png
├── exports/           ← A4 PDFs + 150 dpi PNGs (1240 × 1754 px) of every page
└── assets/            ← empty: the design uses only the standard lockup and the two fonts
```

Note on `exports/`: the PDFs are **raster** (one 150 dpi image per A4 page). Use them to compare sizes and positions at 100 % zoom, not for text extraction.

---

## 1. Page & grid

| | |
|---|---|
| Page | A4 portrait, 210 × 297 mm, background white `#FFFFFF` |
| Margins | 15 mm on all four sides |
| Content box | 180 × 267 mm, x 15 → 195 mm, y 15 → 282 mm (from page top) |
| Horizontal grid | Two anchor columns used throughout: **left 0–86 mm** and **right 94–180 mm** (8 mm gutter). Parties use 3 columns: 0–58, 65–123, 130–180 mm. Table columns in §6. |
| Vertical rhythm | Blocks stack top to bottom with the gaps listed in §3. Footer is pinned to the bottom of the content box. |

---

## 2. Colours

| Name | Hex | Used for |
|---|---|---|
| Ink | `#101314` | All primary text, all heavy rules (0.5 / 0.75 / 1.5 pt), total-due fill, placeholder tag border |
| White | `#FFFFFF` | Page; amount text in total-due box |
| Paper | `#F3F2EE` | “Net à payer / Total due” label inside the ink box |
| Signal Lime | `#C6F24E` | **Fills only**: title marker block, 1.2 mm bar above total due. Never text. |
| Lime Deep | `#526B08` | Small accent text: section labels (Émetteur, Facturé à…), draft note |
| Secondary text | `#4A4F52` | Line detail, line numbers, units, meta keys, footer text, “Suite page n →” (8.6 : 1 on white) |
| Hairline | `#C4C2BB` | 0.25 pt row separators (table, meta, totals, bank, amount-in-words) |
| Watermark | `#ECEAE4` | Draft watermark text, solid colour (no transparency) |

Black-and-white: lime prints as a very light grey and carries no meaning; every state is expressed in words (status row, “BROUILLON”, labels). No shadows, gradients, transparency or rounded boxes.

---

## 3. Blocks, top to bottom (first page)

y values are from the **top of the content box** and measured on the reference (FR issued); they shift with content.

### 3.1 Header — y 0
- **Logo** (left, x 0): DI Xpertia horizontal lockup, **52 × 11.4 mm**, top-aligned at y 0. Trim the transparent padding from the PNG first (the visible artwork is pixels x 265–1540, y 120–400 of the 1800 × 520 file).
- **Title block** (right-aligned to x 180), stacked, right edges aligned, 2 mm gaps:
  1. Title “FACTURE” / “INVOICE” — style **T-Title**, followed by the lime marker: filled rectangle **3 × 6.4 mm**, 2.2 mm to the right of the word, vertically centred on it. The word ends 5.2 mm before x 180.
  2. Document number, e.g. `FA-2026-0042` — **T-DocNo**.
  3. Drafts only: draft note — **T-DraftNote**, Lime Deep.

### 3.2 Header rule — y ≈ 20.5
0.75 pt Ink, full width (0–180). 7 mm below the bottom of the header block; 6 mm above the parties.

### 3.3 Parties — y ≈ 27.5, three columns
Each column: section label (**T-Label**, Lime Deep), then 1.8 mm gap, then the body.

| Column | x | Width | Align | Content |
|---|---|---|---|---|
| Seller (Émetteur / From) | 0 | 58 mm | left | “DI Xpertia SUARL” (**T-PartyName**); address line 1, line 2 (**T-Body**); phone, e-mail, MF, RNE (**T-BodyMono**). Placeholder tag after e-mail, MF, RNE. |
| Client (Facturé à / Bill to) | 65 | 58 mm | left | Client name (**T-PartyName**); address, 1–4 lines (**T-Body**); 1 mm extra gap; tax-ID line `MF …` / `Tax ID …` (**T-BodyMono**) + tag. For a foreign client: `VAT No. …` or omit the line. |
| Document (Facture / Invoice) | 130 | 50 mm | key left, value right | Key–value rows: Numéro, Date d’émission, Échéance, [Statut — drafts only], Devise. Key **T-MetaKey**, value **T-MetaVal** right-aligned to x 180. Each row 1.3 mm top/bottom padding, 0.25 pt Hairline below. |

### 3.4 Line table — 9 mm below the tallest party column (≈ y 69)
See §6.

### 3.5 Totals — last page only, 5 mm below the table, right-aligned
Block **86 mm wide, x 94 → 180**. Rows (label left, amount right-aligned to x 180), each 1.6 mm top/bottom padding, 0.25 pt Hairline below:
1. Total HT / Total excl. VAT — label **T-TotalLabel** (500), amount **T-TotalAmt** (500).
2. One row **per VAT rate used**, highest rate first: label `TVA 19 %` + base `sur 3 600,000` (**T-TotalBase**, 2 mm after the label), amount = base × rate.
3. Stamp duty (Droit de timbre / Stamp duty) + placeholder tag. Amount `1,000` / `1.000`.
4. 3 mm gap, then **lime bar**: filled rect 86 × 1.2 mm, Signal Lime.
5. **Total due box** immediately below the bar: filled rect 86 mm wide, Ink, padding 3.5 mm top/bottom × 4 mm left/right (≈ 12.5 mm tall). Label “NET À PAYER” / “TOTAL DUE” (**T-NetLabel**, Paper) left; amount with currency, e.g. `4 927,000 TND` (**T-NetAmt**, White) right; baselines aligned.
   - Ink-saving alternative (optional): no fill, 1.5 pt Ink border on left/right/bottom, label and amount in Ink.

### 3.6 Amount in words — full width, 4 mm below the totals block
x 0 → 180. 0.25 pt Hairline above and below, 2.5 mm padding. **T-Body** at 8 pt; prefix in regular, the amount words in **semibold (600)**, ending with a full stop.
- FR: `Arrêtée la présente facture à la somme de quatre mille neuf cent vingt-sept dinars.`
- EN: `Amount due: four thousand nine hundred twenty-seven dinars.`
- Millimes/cents, when non-zero: `… dinars et cinq cents millimes` / `… dinars and five hundred millimes`; EUR: `euros` / `cents`.

### 3.7 Payment — 7 mm below the amount in words, two columns
| Column | x | Width | Content |
|---|---|---|---|
| Payment terms | 0 | 86 mm | Label (**T-Label**); 1.8 mm; terms sentence (**T-Body**); 1.8 mm; late-payment sentence (**T-Small**, Secondary) + tag |
| Bank details | 94 | 86 mm | Label + tag; 1.8 mm; rows: key 16 mm (**T-BankKey**), 2 mm gap, value (**T-BankVal**). Each row 1 mm padding, 0.25 pt Hairline below. Rows: Banque/Bank, Titulaire/Account holder, RIB, IBAN, BIC. |

### 3.8 Export mention — client abroad only (replaces the VAT rows in 3.5)
In the totals block, in place of all VAT-rate rows: one row `TVA` / `VAT` with amount `0.00`, followed (same row block, 1.2 mm gap) by the exemption mention in **T-Small**, Secondary, wrapping inside the 86 mm, + tag. No stamp-duty row. Currency EUR or USD, **2 decimals**. See `reference/Facture DI Xpertia.dc.html`, page 5.

### 3.9 Footer — every page, bottom of content box
- 0.5 pt Ink rule, full width, at **y ≈ 261.7** (bottom-anchored: the footer text baseline sits ~2 mm above y 267).
- 2 mm below the rule, one line, **T-Footer**:
  - left: `DI Xpertia SUARL · MF 1997239T/A/M/000 · Rue de Pasteur, Dar Chaabane El Fehri, 8011 Nabeul, Tunisie` (EN: `Tax ID`, `Tunisia`)
  - right (Ink, not grey), right-aligned to x 180: `Page 1 / 2`
- Nothing of the body may come closer than **6 mm** above the footer rule.

---

## 4. Type styles

Fonts: **Space Grotesk** (400, 500, 600, 700) and **JetBrains Mono** (400, 500, 700), both embedded. JetBrains Mono is used for every number, date, reference and amount; its figures are already fixed-width (tabular).

Letter spacing is given in em and as ReportLab `charSpace` (pt).

| Style | Font | Size | Weight | Leading | Tracking | Colour | Case |
|---|---|---|---|---|---|---|---|
| T-Title | Space Grotesk | 22 pt | 700 | 22 pt | 0.10 em (2.2 pt) | Ink | caps |
| T-DocNo | JetBrains Mono | 10.5 pt | 500 | 10.5 pt | 0 | Ink | — |
| T-DraftNote | JetBrains Mono | 7 pt | 500 | 7 pt | 0.04 em (0.28 pt) | Lime Deep | — |
| T-Label (section labels) | JetBrains Mono | 6.5 pt | 500 | 6.5 pt | 0.14 em (0.91 pt) | Lime Deep | caps |
| T-PartyName | Space Grotesk | 9 pt | 700 | 13.5 pt | 0 | Ink | — |
| T-Body | Space Grotesk | 8 pt | 400 | 12 pt (1.5) | 0 | Ink | — |
| T-BodyMono | JetBrains Mono | 7.5 pt | 400 | 12 pt | 0 | Ink | — |
| T-MetaKey | Space Grotesk | 7.5 pt | 400 | 9.75 pt | 0 | Secondary | — |
| T-MetaVal | JetBrains Mono | 7.5 pt | 500 | 9.75 pt | 0 | Ink | — |
| T-TableHead | JetBrains Mono | 6.5 pt | 500 | 7.8 pt | 0.10 em (0.65 pt) | Ink | caps |
| T-LineNo | JetBrains Mono | 7.5 pt | 400 | 10.1 pt | 0 | Secondary | — |
| T-LineTitle | Space Grotesk | 8.5 pt | 500 | 11.5 pt (1.35) | 0 | Ink | — |
| T-LineDetail | Space Grotesk | 7.5 pt | 400 | 10.5 pt (1.4) | 0 | Secondary | — |
| T-LineNum (qty, prices, rate) | JetBrains Mono | 8 pt | 400 | 10.8 pt | 0 | Ink | — |
| T-LineTotal | JetBrains Mono | 8 pt | 500 | 10.8 pt | 0 | Ink | — |
| T-Unit | JetBrains Mono | 6.5 pt | 400 | 7.8 pt | 0 | Secondary | — |
| T-TotalLabel | Space Grotesk | 8 pt | 400 (500 for Total HT) | 10.4 pt | 0 | Ink | — |
| T-TotalAmt | JetBrains Mono | 8 pt | 400 (500 for Total HT) | 10.4 pt | 0 | Ink | — |
| T-TotalBase | JetBrains Mono | 7 pt | 400 | 9.1 pt | 0 | Secondary | — |
| T-NetLabel | JetBrains Mono | 7.5 pt | 500 | 7.5 pt | 0.14 em (1.05 pt) | Paper | caps |
| T-NetAmt | JetBrains Mono | 15 pt | 700 | 15 pt | 0 | White | — |
| T-Small | Space Grotesk | 7.5 pt (7 pt in export mention) | 400 | 1.5 × size | 0 | Secondary | — |
| T-BankKey | Space Grotesk | 7 pt | 400 | 9.45 pt | 0 | Secondary | — |
| T-BankVal | JetBrains Mono | 7.5 pt | 400 | 10.1 pt | 0 | Ink | — |
| T-Carry (“Suite page 2 →”) | JetBrains Mono | 7 pt | 500 | 7 pt | 0.06 em (0.42 pt) | Secondary | — |
| T-ContHeader | JetBrains Mono | 8.5 pt | 500 | 8.5 pt | 0 | Ink | — |
| T-Footer | JetBrains Mono | 6.5 pt | 400 | 9.1 pt | 0 | Secondary (page no. Ink) | — |
| T-Tag (placeholder, remove in prod) | JetBrains Mono | 5.5 pt | 500 | 5.5 pt | 0.08 em | Ink | caps |
| T-Watermark | Space Grotesk | 104 pt | 700 | — | 0.06 em (6.24 pt) | Watermark | caps |

Minimum production text size: 6.5 pt.

---

## 5. Rules, borders, fills

| Element | Weight | Colour |
|---|---|---|
| Header rule (and continuation-header rule) | 0.75 pt | Ink |
| Table: top of header row | 1.5 pt | Ink |
| Table: bottom of header row | 0.5 pt | Ink |
| Table: row separators (below each row) | 0.25 pt | Hairline |
| Meta rows, totals rows, bank rows, amount-in-words top & bottom | 0.25 pt | Hairline |
| Footer rule | 0.5 pt | Ink |
| Total-due box (outline variant) | 1.5 pt, no top edge | Ink |
| Placeholder tag | 0.5 pt dashed (≈ 1.5 pt on / 1.5 pt off), padding 0.5 × 1 mm | Ink |
| Lime title marker | fill 3 × 6.4 mm | Signal Lime |
| Lime bar above total | fill 86 × 1.2 mm | Signal Lime |
| Total-due box | fill 86 × ≈12.5 mm | Ink |

---

## 6. Line table

Full width 0 → 180 mm. Six columns, **2 mm gutters** (5 × 2 = 10 mm):

| # | Column | x from | Width | Align | Content |
|---|---|---|---|---|---|
| 1 | `#` | 0 | 8 mm | left | `01`, `02`… (**T-LineNo**) |
| 2 | Désignation / Description | 10 | 80 mm | left | Title (**T-LineTitle**), 0.6 mm gap, detail (**T-LineDetail**, wraps 1–3 lines) |
| 3 | Qté / Qty | 92 | 15 mm | right | Quantity (**T-LineNum**); 0.6 mm below, unit (**T-Unit**): jours/days, forfait/fixed, mois/month… |
| 4 | PU HT / Unit excl. VAT | 109 | 26 mm | right | **T-LineNum** |
| 5 | TVA / VAT | 137 | 13 mm | right | `19 %` (FR, no-break space) / `19%` (EN) |
| 6 | Total HT / Total excl. VAT | 152 | 28 mm | right | **T-LineTotal** |

- **Header row**: 1.5 pt Ink line on top, 0.5 pt Ink line at bottom, 2 mm top/bottom padding, labels **T-TableHead**, aligned like their columns. No fill.
- **Body rows**: 2.2 mm top/bottom padding, 0.25 pt Hairline below. All cells top-aligned on the **first baseline** of the title. No zebra fill.
- Amount cells contain no currency; the currency appears only in the total due and the meta “Devise” row.

### Page 2 and later (see `exports/04-two-page-*`)
- Split **between rows only** (never inside a row). ReportLab: `LongTable`/`Table` with `repeatRows=1`, `splitByRow=1`, row cells as `Paragraph`s.
- On every page except the last, after the last row: `Suite page 2 →` / `Continued on page 2 →` (**T-Carry**), right-aligned, 2 mm below the table.
- **Continuation header** (pages ≥ 2) replaces 3.1–3.3:
  - Logo 38 × 8.35 mm at x 0, y 0, vertically centred with
  - right-aligned text `FACTURE FA-2026-0043 · suite` / `INVOICE FA-2026-0043 · continued` (**T-ContHeader**).
  - 0.75 pt Ink rule 5 mm below; table header row 5 mm below that rule, repeated identically.
- **Totals, amount in words and payment appear only on the last page**, kept together as one block (`KeepTogether`). If they don’t fit under the last rows, move the last 1–2 rows to a new page with them, so the totals are never alone on a page.
- Footer with `Page n / N` on every page.
- Reference split: 13 rows on page 1 (≈ 6 mm free above the footer), 7 rows + totals on page 2.

---

## 7. Draft state (see `exports/03-draft.pdf`)
- Number: provisional `BR-0057` in the title block and the Numéro row.
- Draft note under the number: `Numéro attribué à la validation` / `Number assigned on approval` (**T-DraftNote**).
- Extra meta row: `Statut : Brouillon` / `Status: Draft`.
- **Watermark**: text `BROUILLON` / `DRAFT`, **T-Watermark** (Space Grotesk 700, 104 pt, tracking 0.06 em), colour `#ECEAE4` solid, **rotated 35° counter-clockwise** (rising left to right), centred on the **page centre (105, 148.5 mm)**, drawn **first**, under all content. Appears on every page of a draft.
- Everything else identical to the issued invoice.

---

## 8. French / English wording

Same layout, only words and number formats change. French runs up to ~20 % longer; every label column has room for it.

| Key | Français | English |
|---|---|---|
| Title | FACTURE | INVOICE |
| Seller label | Émetteur | From |
| Client label | Facturé à | Bill to |
| Document label | Facture | Invoice |
| Meta: number | Numéro | Number |
| Meta: issue date | Date d’émission | Issue date |
| Meta: due date | Échéance | Due date |
| Meta: status (draft) | Statut | Status |
| Status value | Brouillon | Draft |
| Meta: currency | Devise | Currency |
| Seller/client tax ID prefix | MF | Tax ID |
| Foreign client tax ID prefix | N° TVA | VAT No. |
| Country | Tunisie | Tunisia |
| Col 1 | # | # |
| Col 2 | Désignation | Description |
| Col 3 | Qté | Qty |
| Col 4 | PU HT | Unit excl. VAT |
| Col 5 | TVA | VAT |
| Col 6 | Total HT | Total excl. VAT |
| Total excl. VAT | Total HT | Total excl. VAT |
| VAT row | TVA 19 % sur 3 600,000 | VAT 19% on 3,600.000 |
| Stamp duty | Droit de timbre | Stamp duty |
| Total due | Net à payer | Total due |
| Amount in words prefix | Arrêtée la présente facture à la somme de | Amount due: |
| Currency words (TND) | dinar(s), millime(s) | dinar(s), millime(s) |
| Currency words (EUR) | euro(s), centime(s) | euro(s), cent(s) |
| Payment terms label | Conditions de paiement | Payment terms |
| Terms sentence | Virement bancaire à 30 jours date de facture, au plus tard le {due}. | Bank transfer within 30 days of the invoice date, by {due} at the latest. |
| Late payment | Tout retard de paiement entraîne des pénalités au taux de [X] % par mois de retard. | Late payments incur a penalty of [X]% per month of delay. |
| Bank label | Coordonnées bancaires | Bank details |
| Bank rows | Banque · Titulaire · RIB · IBAN · BIC | Bank · Account holder · RIB · IBAN · BIC |
| VAT exemption row | TVA | VAT |
| Exemption mention | Exonération de TVA — exportation de services (art. [X] du Code de la TVA) | VAT exempt — export of services (art. [X], Tunisian VAT Code) |
| Draft watermark | BROUILLON | DRAFT |
| Draft note | Numéro attribué à la validation | Number assigned on approval |
| Carry-over | Suite page {n} → | Continued on page {n} → |
| Continuation header | FACTURE {no} · suite | INVOICE {no} · continued |
| Page number | Page {n} / {N} | Page {n} / {N} |
| Placeholder tag (design only) | À confirmer | To confirm |

### Number and date formats
| | Français | English |
|---|---|---|
| Amount (TND, 3 decimals) | `4 200,000` — thousands: no-break space U+00A0; decimal: comma | `4,200.000` — thousands: comma; decimal: point |
| Amount (EUR/USD, 2 decimals) | `4 000,00` | `4,000.00` |
| With currency (total due only) | `4 927,000 TND` (no-break space before the code) | `4,927.000 TND` |
| Quantity | `2,5` | `2.5` |
| VAT rate | `19 %` (no-break space) | `19%` |
| Date | `17 oct. 2026` (lower-case abbreviated month + period: janv. févr. mars avr. mai juin juil. août sept. oct. nov. déc.) | `Oct 17, 2026` (Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec) |
| Line numbers | `01`, `02`… (2 digits) | same |

### Calculation rules shown in the design
- Line total = qty × unit price; Total HT = sum of line totals.
- VAT per rate = (sum of line totals at that rate) × rate, rounded to 3 decimals (TND).
- Total due = Total HT + Σ VAT + stamp duty.
- Reference: FR/EN issued → Total HT 4 200,000; TVA 19 % 684,000; TVA 7 % 42,000; timbre 1,000; **Net à payer 4 927,000 TND**.

---

## 9. Placeholders — [TO CONFIRM]

Shown in the design with a dashed “À confirmer / To confirm” tag; the tag is a design marker only and must **not** be printed in production.

| # | Field | Placeholder value in the design | Depends on |
|---|---|---|---|
| 1 | Seller matricule fiscal | `1997239T/A/M/000` (also in the footer) | #189 |
| 2 | Seller RNE number | `1997239T` | #189 |
| 3 | Seller e-mail | `contact@dixpertia.tn` | — |
| 4 | Client matricule fiscal | `0000000X/A/M/000` | #189 |
| 5 | Foreign client VAT number (or line omitted) | `FR 00 000000000` | foreign-client question |
| 6 | Stamp duty (timbre fiscal) amount and whether it applies to foreign clients | `1,000 TND`; omitted on the client-abroad page | #189 |
| 7 | Late-payment penalty rate and wording | `[X] % par mois` | #189 |
| 8 | Bank name | `[Nom de la banque]` / `[Bank name]` | — |
| 9 | RIB | `00 000 0000000000000 00` | — |
| 10 | IBAN | `TN59 0000 0000 0000 0000 0000` | — |
| 11 | BIC | `XXXXTNTT` | — |
| 12 | VAT exemption mention for export of services (article number and exact wording) | `art. [X] du Code de la TVA` | foreign-client question |
| 13 | Currency for clients abroad (EUR or USD) | EUR | foreign-client question |

Client names, addresses and line items in the references are sample content.
