"""The invoice PDF, in the layout designed in Claude Design (#194).

The spec is design/invoice-v2/README.md: every size, gap, colour and type
style below comes from it, in mm or pt, and the section numbers in the
comments (§3.1...) point to it. The HTML references next to it are for
reading only; this is the layout rebuilt in ReportLab.

Ink & Signal Lime, as in the app: ink for text and rules, Lime Deep for the
section labels, Signal Lime only as a fill - never as text. Space Grotesk for
words, JetBrains Mono for every number, date, reference and amount. Both
fonts are embedded (app/assets/fonts, OFL), so the PDF renders the same on
any machine. The logo is the lockup the app ships in public/brand/.

Every word comes from app.i18n, in invoice_data["locale"] - the client's
(#135). One generator for a draft (#118: provisional BR- reference, a note
and a watermark) and for an issued invoice.

The PDF computes nothing the books do not have: the amount due is the stored
montant_ttc, and the VAT rows add up to it exactly (see _vat_rows). A seller
detail left empty in the settings is not printed at all, so no placeholder
ever reaches a real invoice (#189 fills them).

The accountant's processing_status is deliberately NOT printed: it is an
internal bookkeeping state, and the client has no business seeing whether
their invoice has been reconciled yet.
"""

from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, Image, KeepTogether, PageTemplate, Paragraph,
                                Spacer, Table, TableStyle)

from app.i18n import CATALOG, DEFAULT_LOCALE, t
from app.services.amount_in_words import CURRENCIES, amount_in_words

ROOT = Path(__file__).resolve().parents[2]
FONTS = ROOT / "app" / "assets" / "fonts"
LOGO = ROOT / "public" / "brand" / "lockup-horizontal.png"

# §2 Colours.
INK = colors.HexColor("#101314")
WHITE = colors.white
PAPER = colors.HexColor("#F3F2EE")
LIME = colors.HexColor("#C6F24E")           # fills only
LIME_DEEP = colors.HexColor("#526B08")      # section labels, draft note
SECONDARY = colors.HexColor("#4A4F52")      # 8.6:1 on white
HAIRLINE = colors.HexColor("#C4C2BB")
WATERMARK = colors.HexColor("#ECEAE4")      # solid: no transparency

# §4 Fonts. Space Grotesk has no static 600; its 700 stands in for it.
SANS, SANS_MEDIUM, SANS_BOLD = "SpaceGrotesk", "SpaceGrotesk-Medium", "SpaceGrotesk-Bold"
MONO, MONO_MEDIUM, MONO_BOLD = "JetBrainsMono", "JetBrainsMono-Medium", "JetBrainsMono-Bold"


def _register_fonts() -> None:
    for name, file in ((SANS, "SpaceGrotesk-Regular.ttf"), (SANS_MEDIUM, "SpaceGrotesk-Medium.ttf"),
                       (SANS_BOLD, "SpaceGrotesk-Bold.ttf"), (MONO, "JetBrainsMono-Regular.ttf"),
                       (MONO_MEDIUM, "JetBrainsMono-Medium.ttf"), (MONO_BOLD, "JetBrainsMono-Bold.ttf")):
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, str(FONTS / file)))
    pdfmetrics.registerFontFamily(SANS, normal=SANS, bold=SANS_BOLD, italic=SANS, boldItalic=SANS_BOLD)
    pdfmetrics.registerFontFamily(MONO, normal=MONO, bold=MONO_BOLD, italic=MONO, boldItalic=MONO_BOLD)


_register_fonts()

# §1 Page and grid: A4, 15 mm margins, a 180 mm content box.
PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
WIDTH = PAGE_W - 2 * MARGIN
TOP = PAGE_H - MARGIN
# §3.9 The footer rule sits 20.3 mm above the page's bottom edge; the body
# keeps 6 mm clear of it.
FOOTER_RULE_Y = MARGIN + 5.3 * mm
BODY_BOTTOM = FOOTER_RULE_Y + 6 * mm
# §6 Pages 2 and later: logo 8.35 mm, 5 mm, rule, 5 mm, then the table.
CONT_LOGO_W, CONT_LOGO_H = 38 * mm, 8.35 * mm
CONT_TOP = TOP - CONT_LOGO_H - 10 * mm


def _load_logo():
    """The lockup cropped to its drawn content.

    The PNG carries wide transparent margins (its artwork is about 1270 x 280
    of 1800 x 520 px): uncropped, the logo printed small and indented.
    """
    if not LOGO.exists():
        return None
    with PILImage.open(LOGO) as image:
        cropped = image.crop(image.getbbox())
    png = BytesIO()
    cropped.save(png, format="PNG")
    return png.getvalue(), cropped.size[1] / cropped.size[0]


_LOGO = _load_logo()


def _text(value) -> str:
    """A stored value made safe for a ReportLab Paragraph (#86).

    Paragraph parses its text as markup: an unclosed "<b>" in a name made the
    whole PDF fail, and a NULL address raised TypeError. Missing values become
    an empty string; markup characters are escaped, so stored text prints as is.
    """
    return escape("" if value is None else str(value))


def _lines(value) -> str:
    """Stored multi-line text (an address, a line's detail) as Paragraph markup."""
    return "<br/>".join(_text(line) for line in str(value or "").splitlines())


def _style(name, font, size, color=INK, leading=None, align=TA_LEFT):
    return ParagraphStyle(name, fontName=font, fontSize=size, textColor=color, alignment=align,
                          leading=leading or size * 1.3)


# §4 Type styles. The tracked caps styles (T-Title, T-Label, T-TableHead,
# T-NetLabel...) are drawn by Tracked below: Paragraph has no letter spacing.
DOC_NO = _style("DocNo", MONO_MEDIUM, 10.5, leading=10.5, align=TA_RIGHT)
PARTY_NAME = _style("PartyName", SANS_BOLD, 9, leading=13.5)
BODY = _style("Body", SANS, 8, leading=12)
BODY_MONO = _style("BodyMono", MONO, 7.5, leading=12)
META_KEY = _style("MetaKey", SANS, 7.5, SECONDARY, leading=9.75)
META_VAL = _style("MetaVal", MONO_MEDIUM, 7.5, leading=9.75, align=TA_RIGHT)
LINE_NO = _style("LineNo", MONO, 7.5, SECONDARY, leading=10.1)
LINE_TITLE = _style("LineTitle", SANS_MEDIUM, 8.5, leading=11.5)
LINE_DETAIL = _style("LineDetail", SANS, 7.5, SECONDARY, leading=10.5)
LINE_NUM = _style("LineNum", MONO, 8, leading=10.8, align=TA_RIGHT)
LINE_TOTAL = _style("LineTotal", MONO_MEDIUM, 8, leading=10.8, align=TA_RIGHT)
UNIT = _style("Unit", MONO, 6.5, SECONDARY, leading=7.8, align=TA_RIGHT)
TOTAL_LABEL = _style("TotalLabel", SANS, 8, leading=10.4)
TOTAL_LABEL_HT = _style("TotalLabelHT", SANS_MEDIUM, 8, leading=10.4)
TOTAL_AMT = _style("TotalAmt", MONO, 8, leading=10.4, align=TA_RIGHT)
TOTAL_AMT_HT = _style("TotalAmtHT", MONO_MEDIUM, 8, leading=10.4, align=TA_RIGHT)
NET_AMT = _style("NetAmt", MONO_BOLD, 15, WHITE, leading=15, align=TA_RIGHT)
IN_WORDS = _style("InWords", SANS, 8, leading=12)
SMALL = _style("Small", SANS, 7.5, SECONDARY, leading=11.25)
EXPORT_MENTION = _style("ExportMention", SANS, 7, SECONDARY, leading=10.5)
BANK_KEY = _style("BankKey", SANS, 7, SECONDARY, leading=9.45)
BANK_VAL = _style("BankVal", MONO, 7.5, leading=10.1)


class Tracked(Flowable):
    """One line of letter-spaced text (§4 tracking), aligned in its width."""

    def __init__(self, text, font, size, color=INK, tracking=0.0, align=TA_LEFT, leading=None):
        super().__init__()
        self.text, self.font, self.size, self.color = text, font, size, color
        self.tracking, self.align, self.leading = tracking, align, leading or size

    def text_width(self):
        # The tracking follows every character; the last one's is not part of the word.
        n = len(self.text)
        return pdfmetrics.stringWidth(self.text, self.font, self.size) + self.tracking * max(n - 1, 0)

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return avail_width, self.leading

    def draw(self):
        c = self.canv
        x = self.width - self.text_width() if self.align == TA_RIGHT else 0
        text = c.beginText(x, self.leading - self.size * 0.8)
        text.setFont(self.font, self.size)
        text.setCharSpace(self.tracking)
        text.setFillColor(self.color)
        text.textOut(self.text)
        c.drawText(text)


def _label(key: str, locale: str) -> Tracked:
    """T-Label: a section label, Lime Deep, mono caps."""
    return Tracked(t(key, locale).upper(), MONO_MEDIUM, 6.5, LIME_DEEP, tracking=0.91)


class TitleMark(Flowable):
    """§3.1 FACTURE / INVOICE, right-aligned, with the lime marker after it."""

    def __init__(self, word):
        super().__init__()
        self.word = Tracked(word, SANS_BOLD, 22, INK, tracking=2.2)

    def wrap(self, avail_width, avail_height):
        self.width = avail_width
        return avail_width, 22

    def draw(self):
        c = self.canv
        word_end = self.width - 5.2 * mm
        x = word_end - self.word.text_width()
        text = c.beginText(x, 22 - 22 * 0.8)
        text.setFont(SANS_BOLD, 22)
        text.setCharSpace(2.2)
        text.setFillColor(INK)
        text.textOut(self.word.text)
        c.drawText(text)
        # 3 x 6.4 mm, 2.2 mm after the word, centred on its capitals.
        cap_middle = 22 - 22 * 0.8 + 22 * 0.7 / 2
        c.setFillColor(LIME)
        c.rect(word_end + 2.2 * mm, cap_middle - 3.2 * mm, 3 * mm, 6.4 * mm, stroke=0, fill=1)


class Rule(Flowable):
    """A filled bar or a rule: the lime bar above the total (§3.5) and the header rule (§3.2)."""

    def __init__(self, width, thickness, color, align="LEFT"):
        super().__init__()
        self.width, self.thickness, self.color, self.hAlign = width, thickness, color, align

    def wrap(self, avail_width, avail_height):
        return self.width, self.thickness

    def draw(self):
        self.canv.setFillColor(self.color)
        self.canv.rect(0, 0, self.width, self.thickness, stroke=0, fill=1)


class TailRows(Flowable):
    """The last line of the table, kept with the totals (§6).

    The totals never stand alone on a page: the last line goes with them.
    Where it continues the table on the same page it is drawn without a
    header; where it opens a new page, the column headers come with it, as
    the table's own repeated header would.
    """

    def __init__(self, doc, with_header: Table, without_header: Table):
        super().__init__()
        self.doc, self.with_header, self.without_header = doc, with_header, without_header
        self.chosen = without_header

    def wrap(self, avail_width, avail_height):
        frame = getattr(self.doc, "frame", None)
        self.chosen = self.with_header if frame is None or frame._atTop else self.without_header
        self.width, self.height = self.chosen.wrap(avail_width, avail_height)
        return self.width, self.height

    def draw(self):
        self.chosen.drawOn(self.canv, 0, 0)


# --- Numbers --------------------------------------------------------------------------

def _decimals(currency: str) -> int:
    return CURRENCIES.get(currency, CURRENCIES["TND"])["digits"]


def _number(value, locale: str, decimals: int) -> str:
    """'4 200,000' / '4,200.000' (§8): U+00A0 between thousands in French."""
    quantum = Decimal(1).scaleb(-decimals)
    text = f"{Decimal(str(value or 0)).quantize(quantum, rounding=ROUND_HALF_UP):,.{decimals}f}"
    return text.replace(",", " ").replace(".", ",") if locale == "fr" else text


def _quantity(value, locale: str) -> str:
    """'2,5' / '2.5', '12' rather than '12.00'."""
    text = format(Decimal(str(value or 0)).normalize(), "f")
    return text.replace(".", ",") if locale == "fr" else text


def _rate(value, locale: str) -> str:
    """'19 %' with a no-break space in French, '19%' in English."""
    text = _quantity(value, locale)
    return f"{text} %" if locale == "fr" else f"{text}%"


def _vat_rows(items, subtotal: Decimal, total: Decimal, decimals: int):
    """(rate, base, vat) per rate used, highest first (§3.5).

    Each rate's VAT is its base times the rate. The amounts are stored rounded
    while the lines are not, so the sum can differ from the stored total by a
    rounding step: the difference goes on the highest rate's row, so that the
    rows add up to exactly the amount due the books hold.
    """
    bases = defaultdict(Decimal)
    for item in items:
        bases[Decimal(str(item.get("vat_rate") or 0))] += Decimal(str(item.get("total") or 0))
    quantum = Decimal(1).scaleb(-decimals)
    rows = [[rate, base, (base * rate / 100).quantize(quantum, rounding=ROUND_HALF_UP)]
            for rate, base in sorted(bases.items(), reverse=True)]
    if rows:
        rows[0][2] += (total - subtotal) - sum(row[2] for row in rows)
    return rows


# --- The seller -----------------------------------------------------------------------

def default_seller() -> dict:
    """The seller as configured (.env, #194); empty values are not printed."""
    from app.core.config import settings

    return {
        "name": settings.SELLER_NAME, "address": settings.SELLER_ADDRESS, "city": settings.SELLER_CITY,
        "phone": settings.SELLER_PHONE, "email": settings.SELLER_EMAIL,
        "tax_id": settings.SELLER_TAX_ID, "rne": settings.SELLER_RNE,
        "bank_name": settings.SELLER_BANK_NAME, "bank_holder": settings.SELLER_BANK_HOLDER,
        "rib": settings.SELLER_RIB, "iban": settings.SELLER_IBAN, "bic": settings.SELLER_BIC,
    }


def _seller_block(seller: dict, locale: str) -> list:
    block = [Paragraph(_text(seller.get("name") or "DI Xpertia"), PARTY_NAME)]
    address = [seller.get("address"), ", ".join(filter(None, [seller.get("city"), t("pdf.country", locale)]))]
    block.append(Paragraph("<br/>".join(_text(line) for line in address if line), BODY))
    mono = [seller.get("phone"), seller.get("email")]
    if seller.get("tax_id"):
        mono.append(f"{t('pdf.tax_id', locale)} {seller['tax_id']}")
    if seller.get("rne"):
        mono.append(f"{t('pdf.rne', locale)} {seller['rne']}")
    if any(mono):
        block.append(Paragraph("<br/>".join(_text(line) for line in mono if line), BODY_MONO))
    return block


def _party_block(name, address, tax_id=None, tax_label="") -> list:
    block = [Paragraph(_text(name), PARTY_NAME)]
    if address:
        block.append(Paragraph(_lines(address), BODY))
    if tax_id:
        # §3.3 1 mm below the address; printed only when filled (#195).
        block += [Spacer(1, 1 * mm), Paragraph(_text(f"{tax_label} {tax_id}"), BODY_MONO)]
    return block


def _footer_text(seller: dict, locale: str) -> str:
    parts = [seller.get("name") or "DI Xpertia"]
    if seller.get("tax_id"):
        parts.append(f"{t('pdf.tax_id', locale)} {seller['tax_id']}")
    parts.append(", ".join(filter(None, [seller.get("address"), seller.get("city"), t("pdf.country", locale)])))
    return " · ".join(parts)


# --- Pages ----------------------------------------------------------------------------

def _canvas_class(locale: str):
    """A canvas that knows the page count: 'Page n / N' and the carry-over (§3.9, §6)."""

    class NumberedCanvas(Canvas):
        def __init__(self, *args, **kwargs):
            # Every page starts in the brand font: ReportLab's default canvas
            # declares Helvetica on each page even when nothing uses it.
            kwargs.setdefault("initialFontName", SANS)
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                n = self._pageNumber
                self.setFont(MONO, 6.5)
                self.setFillColor(INK)
                self.drawRightString(MARGIN + WIDTH, FOOTER_RULE_Y - 2 * mm - 6.5 * 0.8,
                                     t("pdf.page", locale, n=n, total=total))
                if n < total:
                    carry = t("pdf.carry", locale, n=n + 1)
                    width = pdfmetrics.stringWidth(carry, MONO_MEDIUM, 7) + 0.42 * (len(carry) - 1)
                    text = self.beginText(MARGIN + WIDTH - width, BODY_BOTTOM - 2 * mm - 7 * 0.8)
                    text.setFont(MONO_MEDIUM, 7)
                    text.setCharSpace(0.42)
                    text.setFillColor(SECONDARY)
                    text.textOut(carry)
                    self.drawText(text)
                super().showPage()
            super().save()

    return NumberedCanvas


def _on_page(locale: str, seller: dict, number: str, draft: bool, later: bool):
    """What every page carries under its content: watermark, footer, continuation header."""

    def draw(canvas, doc):
        canvas.saveState()
        if draft:
            # §7 Drawn first, under everything; solid colour, rising 35 degrees.
            word = t("pdf.draft", locale)
            canvas.translate(PAGE_W / 2, PAGE_H / 2)
            canvas.rotate(35)
            width = pdfmetrics.stringWidth(word, SANS_BOLD, 104) + 6.24 * (len(word) - 1)
            text = canvas.beginText(-width / 2, -104 * 0.35)
            text.setFont(SANS_BOLD, 104)
            text.setCharSpace(6.24)
            text.setFillColor(WATERMARK)
            text.textOut(word)
            canvas.drawText(text)
            canvas.restoreState()
            canvas.saveState()
        # §3.9 Footer rule and line; the page number is added once the count is known.
        canvas.setStrokeColor(INK)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, FOOTER_RULE_Y, MARGIN + WIDTH, FOOTER_RULE_Y)
        canvas.setFont(MONO, 6.5)
        canvas.setFillColor(SECONDARY)
        canvas.drawString(MARGIN, FOOTER_RULE_Y - 2 * mm - 6.5 * 0.8, _footer_text(seller, locale))
        if later:
            # §6 Continuation header: the small logo, the document, a rule.
            if _LOGO:
                canvas.drawImage(ImageReader(BytesIO(_LOGO[0])), MARGIN, TOP - CONT_LOGO_H,
                                 CONT_LOGO_W, CONT_LOGO_W * _LOGO[1], mask="auto")
            canvas.setFont(MONO_MEDIUM, 8.5)
            canvas.setFillColor(INK)
            canvas.drawRightString(MARGIN + WIDTH, TOP - CONT_LOGO_H / 2 - 8.5 * 0.35,
                                   t("pdf.continued", locale, number=number))
            canvas.setLineWidth(0.75)
            canvas.line(MARGIN, TOP - CONT_LOGO_H - 5 * mm, MARGIN + WIDTH, TOP - CONT_LOGO_H - 5 * mm)
        canvas.restoreState()

    return draw


# --- The document ---------------------------------------------------------------------

def _header(locale, number, draft) -> list:
    """§3.1 and §3.2: the lockup, the title block, the header rule."""
    if _LOGO:
        logo = Image(BytesIO(_LOGO[0]), width=52 * mm, height=52 * mm * _LOGO[1], hAlign="LEFT")
    else:
        logo = Paragraph("DI Xpertia", PARTY_NAME)
    title = [TitleMark(t("pdf.invoice", locale)), Spacer(1, 2 * mm), Paragraph(_text(number), DOC_NO)]
    if draft:
        # A draft says its legal number comes on approval - never a predicted
        # number, which could be wrong (#118).
        title += [Spacer(1, 2 * mm),
                  Tracked(t("pdf.draft_note", locale), MONO_MEDIUM, 7, LIME_DEEP, tracking=0.28, align=TA_RIGHT)]
    header = Table([[logo, title]], colWidths=[86 * mm, 94 * mm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), *_FLAT]))
    return [header, Spacer(1, 7 * mm), Rule(WIDTH, 0.75, INK), Spacer(1, 6 * mm)]


_FLAT = [("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
         ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
         ("FONTNAME", (0, 0), (-1, -1), SANS)]


def _meta(rows) -> Table:
    """§3.3 Key-value rows of the document column."""
    table = Table([[Paragraph(_text(k), META_KEY), Paragraph(_text(v), META_VAL)] for k, v in rows],
                  colWidths=[22 * mm, 28 * mm])
    table.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1.3 * mm),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1.3 * mm),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.25, HAIRLINE)]))
    return table


# §6 Column widths, each with its 2 mm gutter on the right (none after the last).
COLUMNS = [10 * mm, 82 * mm, 17 * mm, 28 * mm, 15 * mm, 28 * mm]


def _table_head(locale) -> list:
    keys = [("#", TA_LEFT), (t("pdf.col.description", locale), TA_LEFT), (t("pdf.col.qty", locale), TA_RIGHT),
            (t("pdf.col.unit_price", locale), TA_RIGHT), (t("pdf.col.vat", locale), TA_RIGHT),
            (t("pdf.col.total", locale), TA_RIGHT)]
    return [Tracked(label.upper(), MONO_MEDIUM, 6.5, INK, tracking=0.65, align=align, leading=7.8)
            for label, align in keys]


def _line_row(n, item, locale, decimals) -> list:
    description = [Paragraph(_text(item.get("description")), LINE_TITLE)]
    if item.get("detail"):
        description += [Spacer(1, 0.6 * mm), Paragraph(_lines(item["detail"]), LINE_DETAIL)]
    quantity = [Paragraph(_quantity(item.get("qty"), locale), LINE_NUM)]
    if item.get("unit"):
        quantity += [Spacer(1, 0.6 * mm), Paragraph(_text(item["unit"]), UNIT)]
    return [Paragraph(f"{n:02d}", LINE_NO), description, quantity,
            Paragraph(_number(item.get("price"), locale, decimals), LINE_NUM),
            Paragraph(_rate(item.get("vat_rate") or 0, locale), LINE_NUM),
            Paragraph(_number(item.get("total"), locale, decimals), LINE_TOTAL)]


def _lines_table(rows, header: bool) -> Table:
    table = Table(rows, colWidths=COLUMNS, repeatRows=1 if header else 0, splitByRow=1)
    style = [*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("RIGHTPADDING", (0, 0), (-2, -1), 2 * mm),
             ("TOPPADDING", (0, 0), (-1, -1), 2.2 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2 * mm),
             ("LINEBELOW", (0, 0), (-1, -1), 0.25, HAIRLINE)]
    if header:
        style += [("TOPPADDING", (0, 0), (-1, 0), 2 * mm), ("BOTTOMPADDING", (0, 0), (-1, 0), 2 * mm),
                  ("LINEABOVE", (0, 0), (-1, 0), 1.5, INK), ("LINEBELOW", (0, 0), (-1, 0), 0.5, INK)]
    table.setStyle(TableStyle(style))
    return table


def _totals(items, subtotal, total, locale, currency, decimals, export_mention=None) -> list:
    """§3.5 Total HT, VAT per rate, the lime bar, the amount due.

    An export of services (§3.8, #195) has one VAT row at zero instead, with
    the exemption mention under it, and no stamp duty.
    """
    rows = [[Paragraph(_text(t("pdf.total_ht", locale)), TOTAL_LABEL_HT),
             Paragraph(_number(subtotal, locale, decimals), TOTAL_AMT_HT)]]
    if export_mention is not None:
        vat_cell = [Paragraph(_text(t("pdf.col.vat", locale)), TOTAL_LABEL)]
        if export_mention:
            vat_cell += [Spacer(1, 1.2 * mm), Paragraph(_text(export_mention), EXPORT_MENTION)]
        rows.append([vat_cell, Paragraph(_number(0, locale, decimals), TOTAL_AMT)])
    for rate, base, vat in ([] if export_mention is not None else _vat_rows(items, subtotal, total, decimals)):
        label = (f"{_text(t('pdf.vat_row', locale, rate=_rate(rate, locale)))}&nbsp;&nbsp;"
                 f"<font name='{MONO}' size='7' color='{SECONDARY.hexval()}'>"
                 f"{_text(t('pdf.vat_base', locale, base=_number(base, locale, decimals)))}</font>")
        rows.append([Paragraph(label, TOTAL_LABEL), Paragraph(_number(vat, locale, decimals), TOTAL_AMT)])
    block = Table(rows, colWidths=[50 * mm, 36 * mm], hAlign="RIGHT")
    block.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1.6 * mm),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 * mm),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.25, HAIRLINE)]))
    net = Table([[Tracked(t("pdf.net", locale).upper(), MONO_MEDIUM, 7.5, PAPER, tracking=1.05, leading=9),
                  Paragraph(f"{_number(total, locale, decimals)} {_text(currency)}", NET_AMT)]],
                colWidths=[36 * mm, 50 * mm], hAlign="RIGHT")
    net.setStyle(TableStyle([*_FLAT, ("BACKGROUND", (0, 0), (-1, -1), INK), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                             ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
                             ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
                             ("LEFTPADDING", (0, 0), (0, 0), 4 * mm), ("RIGHTPADDING", (-1, 0), (-1, 0), 4 * mm)]))
    return [block, Spacer(1, 3 * mm), Rule(86 * mm, 1.2 * mm, LIME, align="RIGHT"), net]


def _in_words(total, currency, locale) -> Table:
    """§3.6 The amount due in words, between two hairlines."""
    words = amount_in_words(total, currency, locale)
    cell = Paragraph(f"{_text(t('pdf.in_words', locale))} <font name='{SANS_BOLD}'>{_text(words)}</font>.",
                     IN_WORDS)
    table = Table([[cell]], colWidths=[WIDTH])
    table.setStyle(TableStyle([*_FLAT, ("TOPPADDING", (0, 0), (-1, -1), 2.5 * mm),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5 * mm),
                               ("LINEABOVE", (0, 0), (-1, -1), 0.25, HAIRLINE),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.25, HAIRLINE)]))
    return table


def _payment(seller, due_date, locale) -> Table:
    """§3.7 Payment terms, and the bank details once they are configured (#189)."""
    terms = [_label("pdf.terms", locale), Spacer(1, 1.8 * mm)]
    if due_date:
        terms.append(Paragraph(_text(t("pdf.terms_text", locale, due=due_date)), BODY))
    bank_rows = [(t("pdf.bank.name", locale), seller.get("bank_name")),
                 (t("pdf.bank.holder", locale), seller.get("bank_holder")),
                 ("RIB", seller.get("rib")), ("IBAN", seller.get("iban")), ("BIC", seller.get("bic"))]
    bank_rows = [(k, v) for k, v in bank_rows if v]
    bank = ""
    if bank_rows:
        rows = Table([[Paragraph(_text(k), BANK_KEY), Paragraph(_text(v), BANK_VAL)] for k, v in bank_rows],
                     colWidths=[18 * mm, 68 * mm])
        rows.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                  ("TOPPADDING", (0, 0), (-1, -1), 1 * mm),
                                  ("BOTTOMPADDING", (0, 0), (-1, -1), 1 * mm),
                                  ("LINEBELOW", (0, 0), (-1, -1), 0.25, HAIRLINE)]))
        bank = [_label("pdf.bank", locale), Spacer(1, 1.8 * mm), rows]
    table = Table([[terms, "", bank]], colWidths=[86 * mm, 8 * mm, 86 * mm])
    table.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return table


def _export_mention(invoice_data: dict, locale: str) -> str:
    """The VAT exemption mention of an export invoice, from the settings (#195)."""
    if "export_mention" in invoice_data:
        return invoice_data["export_mention"] or ""
    from app.core.config import settings

    return settings.EXPORT_MENTION_FR if locale == "fr" else settings.EXPORT_MENTION_EN


def generate_invoice_pdf(invoice_data: dict, output_path: str = None):
    """Build the invoice PDF; returns its bytes, or writes it to `output_path`."""
    locale = invoice_data.get("locale") or DEFAULT_LOCALE
    number = invoice_data.get("invoice_id") or ""
    draft = bool(invoice_data.get("draft"))
    currency = invoice_data.get("currency") or "TND"
    decimals = _decimals(currency)
    seller = invoice_data.get("seller") or default_seller()
    items = invoice_data.get("items") or []
    subtotal = Decimal(str(invoice_data.get("subtotal") or 0))
    total = Decimal(str(invoice_data.get("total") or 0))
    raw_status = str(invoice_data.get("status") or "").lower()

    target = BytesIO() if output_path is None else output_path
    doc = BaseDocTemplate(target, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                          bottomMargin=MARGIN, title=f"DI Xpertia {number}".strip(), author="DI Xpertia",
                          initialFontName=SANS)
    first = Frame(MARGIN, BODY_BOTTOM, WIDTH, TOP - BODY_BOTTOM, 0, 0, 0, 0, id="first")
    later = Frame(MARGIN, BODY_BOTTOM, WIDTH, CONT_TOP - BODY_BOTTOM, 0, 0, 0, 0, id="later")
    doc.addPageTemplates([
        PageTemplate("first", [first], onPage=_on_page(locale, seller, number, draft, later=False),
                     autoNextPageTemplate="later"),
        PageTemplate("later", [later], onPage=_on_page(locale, seller, number, draft, later=True)),
    ])

    story = _header(locale, number, draft)

    # §3.3 Parties. A bill a supplier sent us (#40) reads the other way round:
    # the supplier is the issuer and DI Xpertia the one billed.
    export = bool(invoice_data.get("export"))
    tax_label = t("pdf.client_vat" if export else "pdf.tax_id", locale)
    counterparty = _party_block(invoice_data.get("client"), invoice_data.get("client_address"),
                                invoice_data.get("client_tax_id"), tax_label)
    us = _seller_block(seller, locale)
    issuer, billed = (counterparty, us) if invoice_data.get("incoming") else (us, counterparty)
    meta = [(t("pdf.meta.number", locale), number),
            (t("pdf.meta.issued", locale), invoice_data.get("date_issued")),
            (t("pdf.meta.due", locale), invoice_data.get("due_date"))]
    # Drafts say so (§7); so do the states a client must not miss - paid,
    # overdue (#117), cancelled. A plain sent invoice needs no status row.
    if draft or raw_status in ("payee", "en_retard", "annulee"):
        key = "pdf.status.brouillon" if draft else f"pdf.status.{raw_status}"
        meta.append((t("pdf.meta.status", locale), t(key, locale) if key in CATALOG else raw_status))
    meta.append((t("pdf.meta.currency", locale), currency))
    parties = Table([[[_label("pdf.seller", locale), Spacer(1, 1.8 * mm), *issuer], "",
                      [_label("pdf.bill_to", locale), Spacer(1, 1.8 * mm), *billed], "",
                      [_label("pdf.document", locale), Spacer(1, 1.8 * mm), _meta(meta)]]],
                    colWidths=[58 * mm, 7 * mm, 58 * mm, 7 * mm, 50 * mm])
    parties.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [parties, Spacer(1, 9 * mm)]

    # §6 Lines; the last one travels with the totals (TailRows).
    head = _table_head(locale)
    rows = [_line_row(n, item, locale, decimals) for n, item in enumerate(items, start=1)]
    if not rows:
        rows = [["", Paragraph(_text(t("pdf.no_items", locale)), LINE_DETAIL), "", "", "", ""]]
    if len(rows) > 1:
        story.append(_lines_table([head, *rows[:-1]], header=True))
    tail = TailRows(doc, _lines_table([head, rows[-1]], header=True), _lines_table([rows[-1]], header=False))
    if len(rows) == 1:
        tail.chosen = tail.without_header = tail.with_header

    # §3.5-3.7 Totals, amount in words and payment: the last page only, together.
    story.append(KeepTogether([
        tail, Spacer(1, 5 * mm),
        *_totals(items, subtotal, total, locale, currency, decimals,
                 export_mention=_export_mention(invoice_data, locale) if export else None),
        Spacer(1, 4 * mm), _in_words(total, currency, locale),
        Spacer(1, 7 * mm), _payment(seller, invoice_data.get("due_date"), locale),
    ]))

    doc.build(story, canvasmaker=_canvas_class(locale))

    if output_path is None:
        return target.getvalue()
    return output_path
