# Brand source — Ink & Signal Lime

Design source of record for the DI Xpertia identity. Only the files the app is
built from are versioned here; `.gitignore` allowlists them one by one.

| File | Used for |
|---|---|
| `exports/logo/DIXpertia-favicon.svg` | browser favicon (thickened for 16–32 px) |
| `exports/logo/DIXpertia-app-icon.svg`, `-app-icon-1024.png` | app icon, apple-touch-icon |
| `exports/logo/DIXpertia-mark-dark.svg`, `-mark-light.svg` | the mark on paper / on ink |
| `exports/logo/DIXpertia-lockup-horizontal.png`, `-on-ink.png` | full logo, preview card |
| `exports/palette/dixpertia-palette.css`, `.json` | colour tokens (`--dix-*`) |

## Rules

- The app never references this folder. Assets are copied into
  `public/brand/` with the embedded C2PA metadata removed, which takes each
  SVG from about 8 KB to about 300 bytes.
- One accent per view. Signal Lime `#C6F24E` never carries running text.
- Lime Deep for accented text on paper is **`#526B08`** in the app, not the
  kit's `#5C7A0A`, which measures 4.42:1 on paper and fails WCAG AA (#23).
- Clear space around the logo is at least the height of the cursor.

The rest of the kit (business card, sign, e-mail signature, LinkedIn cover,
palette swatch page) is kept outside the repository: the print files carry
personal contact details.
