"""The invoice PDF, in the DI Xpertia identity (#81).

Ink & Signal Lime, as in the app (src/index.css): ink for text and rules,
Lime Deep for accented text, Signal Lime only as a fill or a rule - never as
text, it is unreadable on white. Space Grotesk for words, JetBrains Mono for
references, dates and amounts. Both fonts are embedded (app/assets/fonts,
OFL), so the PDF renders the same on any machine. The logo is the lockup the
app ships in public/brand/.

Every word comes from app.i18n, in invoice_data["locale"] - the client's
(#135). One generator for both a draft (#118: provisional BR- reference and a
watermark) and an issued invoice.

The accountant's processing_status is deliberately NOT printed: it is an
internal bookkeeping state, and the client has no business seeing whether
their invoice has been reconciled yet.
"""

from datetime import datetime
from io import BytesIO
from functools import partial
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.i18n import CATALOG, DEFAULT_LOCALE, format_amount, format_date, t

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "app" / "assets" / "fonts"
LOGO = ROOT / "public" / "brand" / "lockup-horizontal.png"
LOGO_WIDTH = 55 * mm

# Ink & Signal Lime (src/index.css). Tints of ink are mixed on white here:
# ReportLab text has no reliable alpha across viewers.
INK = colors.HexColor("#101314")
INK_MUTED = colors.HexColor("#6A6D6E")      # ink at 62% on white
HAIRLINE = colors.HexColor("#DCDDDD")       # ink at 14% on white
PAPER = colors.HexColor("#F3F2EE")
LIME = colors.HexColor("#C6F24E")           # fills and rules only
LIME_DEEP = colors.HexColor("#526B08")      # accented text, 5.4:1 on paper

SANS, SANS_BOLD = "SpaceGrotesk", "SpaceGrotesk-Bold"
MONO, MONO_BOLD = "JetBrainsMono", "JetBrainsMono-Bold"


def _register_fonts() -> None:
    for name, file in ((SANS, "SpaceGrotesk-Regular.ttf"), (SANS_BOLD, "SpaceGrotesk-Bold.ttf"),
                       (MONO, "JetBrainsMono-Regular.ttf"), (MONO_BOLD, "JetBrainsMono-Bold.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
    pdfmetrics.registerFontFamily(SANS, normal=SANS, bold=SANS_BOLD, italic=SANS, boldItalic=SANS_BOLD)
    pdfmetrics.registerFontFamily(MONO, normal=MONO, bold=MONO_BOLD, italic=MONO, boldItalic=MONO_BOLD)


_register_fonts()


def _load_logo():
    """The lockup cropped to its drawn content, and its size on the page.

    The PNG carries wide transparent margins (its content is about 1270 x 280
    of 1800 x 520 px): uncropped, the logo printed small and indented from the
    text below it. Cropped, it prints at about 590 dpi at this width.
    """
    if not LOGO.exists():
        return None
    with PILImage.open(LOGO) as image:
        cropped = image.crop(image.getbbox())
    png = BytesIO()
    cropped.save(png, format="PNG")
    width, height = cropped.size
    return png.getvalue(), LOGO_WIDTH * height / width


_LOGO = _load_logo()


def _text(value) -> str:
    """A stored value made safe for a ReportLab Paragraph (#86).

    Paragraph parses its text as markup. A name or a line containing a known
    tag left open, such as "R&D <b>" or "<i>Acme", made the whole PDF fail
    with ValueError, and a closed one silently changed the formatting instead
    of being printed. A NULL address raised TypeError. Missing values become an
    empty string; markup characters are escaped, so stored text prints as is.
    """
    return escape("" if value is None else str(value))


def _status_label(raw, locale: str) -> str:
    key = f"pdf.status.{str(raw).lower()}"
    return t(key, locale) if key in CATALOG else str(raw)


def _style(name, font=SANS, size=9, color=INK, align=TA_LEFT, leading=None):
    return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color, alignment=align,
                          leading=leading or size * 1.3)


TITLE = _style("Title", SANS_BOLD, 22, INK, TA_RIGHT, leading=24)
TAGLINE = _style("Tagline", SANS, 8, INK_MUTED)
REF = _style("Ref", MONO_BOLD, 10, INK, TA_RIGHT)
REF_NOTE = _style("RefNote", MONO, 7, INK_MUTED, TA_RIGHT)
LABEL = _style("Label", MONO, 7, INK_MUTED)
LABEL_RIGHT = _style("LabelRight", MONO, 7, INK_MUTED, TA_RIGHT)
VALUE = _style("Value", SANS, 9, INK)
VALUE_BOLD = _style("ValueBold", SANS_BOLD, 10, INK)
VALUE_RIGHT = _style("ValueRight", MONO, 9, INK, TA_RIGHT)
STATUS = _style("Status", SANS_BOLD, 9, LIME_DEEP, TA_RIGHT)
HEAD = _style("Head", SANS_BOLD, 8, colors.white)
HEAD_RIGHT = _style("HeadRight", SANS_BOLD, 8, colors.white, TA_RIGHT)
CELL = _style("Cell", SANS, 9, INK)
CELL_NUM = _style("CellNum", MONO, 9, INK, TA_RIGHT)
TOTAL_LABEL = _style("TotalLabel", SANS, 9, INK_MUTED, TA_RIGHT)
TOTAL_NUM = _style("TotalNum", MONO, 9, INK, TA_RIGHT)
GRAND_LABEL = _style("GrandLabel", SANS_BOLD, 11, INK, TA_RIGHT)
GRAND_NUM = _style("GrandNum", MONO_BOLD, 11, INK, TA_RIGHT)
FOOTER = _style("Footer", MONO, 7, INK_MUTED, leading=10)

# The font of plain-string cells too, or ReportLab falls back to Helvetica.
_NO_PADDING = [("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
               ("FONTNAME", (0, 0), (-1, -1), SANS)]
# Every page starts in the brand font: ReportLab's default canvas declares
# Helvetica on each page even when nothing is written in it. The document
# template passes its own initialFontName to the canvas, so it is set there.
_CANVAS = partial(Canvas, initialFontName=SANS)


def _label(key: str, locale: str, right: bool = False) -> Paragraph:
    """A small mono caption, upper case: the app's micro-copy style."""
    return Paragraph(_text(t(key, locale)).upper(), LABEL_RIGHT if right else LABEL)


def _draft_watermark(word: str):
    """A large diagonal DRAFT (or BROUILLON) across every page of a draft's PDF (#118).

    A draft has no legal number yet. Its PDF is what the accountant reviews, and
    it must never pass for an invoice if it is printed or forwarded by mistake.
    """
    def draw(canvas, doc):
        canvas.saveState()
        # Sized to the word: BROUILLON is longer than DRAFT.
        canvas.setFont(SANS_BOLD, 110 if len(word) <= 5 else 80)
        canvas.setFillColor(colors.Color(0.65, 0.23, 0.17, alpha=0.10))
        width, height = A4
        canvas.translate(width / 2, height / 2)
        canvas.rotate(40)
        canvas.drawCentredString(0, -35, word)
        canvas.restoreState()
    return draw


def _lime_rule(width: float, thickness: float = 2.2) -> Table:
    """The single Signal Lime accent: a rule, never text."""
    rule = Table([[""]], colWidths=[width], rowHeights=[thickness])
    rule.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIME), *_NO_PADDING]))
    return rule


def generate_invoice_pdf(invoice_data: dict, output_path: str = None):
    """Build the invoice PDF; returns its bytes, or writes it to `output_path`."""
    if output_path is None:
        buffer = BytesIO()
        target = buffer
    else:
        target = output_path
    doc = SimpleDocTemplate(target, pagesize=A4, topMargin=16 * mm, bottomMargin=16 * mm,
                            leftMargin=18 * mm, rightMargin=18 * mm,
                            title="DI Xpertia", author="DI Xpertia", initialFontName=SANS)
    # The frame's usable width: it pads 6 pt on each side, and a table sized to
    # the full margin width overhung it while the paragraphs did not.
    width = doc.width - 12

    locale = invoice_data.get('locale') or DEFAULT_LOCALE
    invoice_id = _text(invoice_data.get('invoice_id'))
    client = _text(invoice_data.get('client'))
    client_address = invoice_data.get('client_address') or ''
    date_issued = invoice_data.get('date_issued', '')
    due_date = invoice_data.get('due_date', '')
    status = _status_label(invoice_data.get('status', 'envoyee'), locale)
    items = invoice_data.get('items', [])
    subtotal = invoice_data.get('subtotal', 0)
    total = invoice_data.get('total', 0)
    draft = bool(invoice_data.get('draft'))

    story = []

    # --- Header: the lockup on the left, the document on the right ----------
    logo = (Image(BytesIO(_LOGO[0]), width=LOGO_WIDTH, height=_LOGO[1], hAlign="LEFT") if _LOGO
            else Paragraph("DI Xpertia", TITLE))
    brand = [logo, Spacer(1, 2 * mm), Paragraph(_text(t("pdf.tagline", locale)), TAGLINE)]
    # A draft shows its provisional BR- reference and says the legal number
    # comes on approval - never a predicted number, which could be wrong (#118).
    document = [Paragraph(_text(t("pdf.invoice", locale)), TITLE), Spacer(1, 1.5 * mm),
                Paragraph(invoice_id, REF)]
    if draft:
        document.append(Paragraph(_text(t("pdf.draft_note", locale)), REF_NOTE))
    document.append(Paragraph(f"{_text(t('pdf.date', locale))} {_text(date_issued)}", REF_NOTE))
    header = Table([[brand, document]], colWidths=[width * 0.55, width * 0.45])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), *_NO_PADDING]))
    story += [header, Spacer(1, 6 * mm), _lime_rule(width), Spacer(1, 7 * mm)]

    # --- Billed to, and the terms -------------------------------------------
    address = "<br/>".join(_text(line) for line in client_address.split('\n'))
    billed = [_label("pdf.billed_to", locale), Spacer(1, 1.5 * mm),
              Paragraph(client, VALUE_BOLD), Paragraph(address, VALUE)]
    terms = Table([
        [_label("pdf.due_date", locale, right=True), Paragraph(_text(due_date), VALUE_RIGHT)],
        [_label("pdf.status", locale, right=True), Paragraph(_text(status), STATUS)],
    ], colWidths=[width * 0.22, width * 0.23])
    terms.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), *_NO_PADDING,
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    parties = Table([[billed, terms]], colWidths=[width * 0.55, width * 0.45])
    parties.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), *_NO_PADDING]))
    story += [parties, Spacer(1, 9 * mm)]

    # --- Lines ----------------------------------------------------------------
    if items:
        rows = [[Paragraph(_text(t("pdf.description", locale)), HEAD),
                 Paragraph(_text(t("pdf.qty", locale)), HEAD_RIGHT),
                 Paragraph(_text(t("pdf.price", locale)), HEAD_RIGHT),
                 Paragraph(_text(t("pdf.total", locale)), HEAD_RIGHT)]]
        for item in items:
            rows.append([Paragraph(_text(item.get('description')), CELL),
                         Paragraph(_text(item.get('qty', 0)), CELL_NUM),
                         Paragraph(format_amount(item.get('price', 0), locale), CELL_NUM),
                         Paragraph(format_amount(item.get('total', 0), locale), CELL_NUM)])
        lines = Table(rows, colWidths=[width * 0.46, width * 0.10, width * 0.22, width * 0.22], repeatRows=1)
        lines.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("FONTNAME", (0, 0), (-1, -1), SANS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LINEBELOW", (0, 1), (-1, -1), 0.5, HAIRLINE),
        ]))
        story += [lines, Spacer(1, 5 * mm)]

        # --- Totals, right-aligned; the total due under the lime rule -------
        # Same width as the lines, an empty first column: the right edges align.
        totals = Table([
            ["", Paragraph(_text(t("pdf.subtotal", locale)), TOTAL_LABEL),
             Paragraph(format_amount(subtotal, locale), TOTAL_NUM)],
            ["", Paragraph(_text(t("pdf.vat", locale)), TOTAL_LABEL),
             Paragraph(format_amount(round(total - subtotal, 3), locale), TOTAL_NUM)],
            ["", Paragraph(_text(t("pdf.grand_total", locale)), GRAND_LABEL),
             Paragraph(format_amount(total, locale), GRAND_NUM)],
        ], colWidths=[width * 0.50, width * 0.28, width * 0.22])
        totals.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), SANS),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LINEABOVE", (1, 2), (-1, 2), 2.2, LIME),
            ("TOPPADDING", (1, 2), (-1, 2), 7), ("BOTTOMPADDING", (1, 2), (-1, 2), 7),
            ("BACKGROUND", (1, 2), (-1, 2), PAPER),
        ]))
        story.append(totals)
    else:
        story.append(Paragraph(_text(t("pdf.no_items", locale)), VALUE))

    # --- Footer ----------------------------------------------------------------
    rule = Table([[""]], colWidths=[width], rowHeights=[0.5])
    rule.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, -1), 0.5, HAIRLINE), *_NO_PADDING]))
    now = datetime.now()
    generated = t("pdf.generated_on", locale, date=format_date(now, locale), time=now.strftime("%H:%M"))
    # The catalog's footer carries its own <br/>; nothing in it is user data.
    story += [Spacer(1, 14 * mm), rule, Spacer(1, 3 * mm),
              Paragraph(t("pdf.footer", locale), FOOTER), Paragraph(_text(generated), FOOTER)]

    if draft:
        watermark = _draft_watermark(t("pdf.draft", locale))
        doc.build(story, onFirstPage=watermark, onLaterPages=watermark, canvasmaker=_CANVAS)
    else:
        doc.build(story, canvasmaker=_CANVAS)

    if output_path is None:
        buffer.seek(0)
        return buffer.getvalue()
    return output_path
