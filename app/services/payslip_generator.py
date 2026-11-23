"""The payslip PDF (#22): the invoice's identity, fonts and footer, one page of figures.

The PDF computes nothing: gross, net and the year-to-date totals arrive in
`data`, read from the payslips table by the route.
"""

from io import BytesIO

from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle

from app.i18n import DEFAULT_LOCALE, t
from app.services.invoice_generator import (
    BODY, BODY_BOTTOM, HAIRLINE, INK, LIME, MARGIN, MONO_MEDIUM, NET_AMT, PAPER, PARTY_NAME, SANS,
    SECONDARY, TOP, WIDTH, Rule, TitleMark, Tracked, _FLAT, _canvas_class, _header_logo, _label,
    _number, _on_page, _seller_block, _style, _text, default_seller,
)

KEY = _style("PsKey", SANS, 8, SECONDARY, leading=11)
VAL = _style("PsVal", MONO_MEDIUM, 8.5, leading=11, align=TA_RIGHT)
PERIOD = _style("PsPeriod", MONO_MEDIUM, 10.5, leading=10.5, align=TA_RIGHT)
CURRENCY, DECIMALS = "TND", 3


def month_label(day, locale: str) -> str:
    """'octobre 2026' / 'October 2026', the month name from the catalog."""
    return f"{t(f'payslip.month.{day.month}', locale)} {day.year}"


def _money(value, locale: str) -> str:
    return f"{_number(value, locale, DECIMALS)}\u00a0{CURRENCY}"


def _rows(rows) -> Table:
    half = WIDTH / 2 - 5 * mm
    table = Table([[Paragraph(_text(k), KEY), Paragraph(_text(v), VAL)] for k, v in rows],
                  colWidths=[half, half])
    table.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP"),
                               ("TOPPADDING", (0, 0), (-1, -1), 1.6 * mm),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6 * mm),
                               ("LINEBELOW", (0, 0), (-1, -1), 0.25, HAIRLINE)]))
    return table


def generate_payslip_pdf(data: dict) -> bytes:
    locale = data.get("locale") or DEFAULT_LOCALE
    seller = data.get("seller") or default_seller()
    period = data.get("period_label") or ""
    title = f"DI Xpertia {t('payslip.title', locale)} {period}".strip()

    target = BytesIO()
    doc = BaseDocTemplate(target, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN,
                          bottomMargin=MARGIN, title=title, author="DI Xpertia", initialFontName=SANS)
    frame = Frame(MARGIN, BODY_BOTTOM, WIDTH, TOP - BODY_BOTTOM, 0, 0, 0, 0, id="body")
    doc.addPageTemplates([PageTemplate("p", [frame], onPage=_on_page(locale, seller, period, False, later=False))])

    # Header: lockup left, title right, then the rule (same geometry as the invoice).
    head = Table([[_header_logo(), [TitleMark(t("payslip.title", locale).upper()), Spacer(1, 2 * mm),
                                    Paragraph(_text(period), PERIOD)]]],
                 colWidths=[86 * mm, 94 * mm])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), *_FLAT]))
    story = [head, Spacer(1, 7 * mm), Rule(WIDTH, 0.75, INK), Spacer(1, 6 * mm)]

    # Company and employee.
    employee = [_label("payslip.employee", locale), Spacer(1, 1.8 * mm),
                Paragraph(_text(data.get("employee_name")), PARTY_NAME)]
    if data.get("job_title"):
        employee.append(Paragraph(_text(data["job_title"]), BODY))
    employee.append(Paragraph(_text(f"{t('payslip.hired_on', locale)} {data.get('hired_on') or ''}"), BODY))
    parties = Table([[[_label("pdf.seller", locale), Spacer(1, 1.8 * mm), *_seller_block(seller, locale)],
                      "", employee]], colWidths=[86 * mm, 8 * mm, 86 * mm])
    parties.setStyle(TableStyle([*_FLAT, ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [parties, Spacer(1, 9 * mm)]

    # This period: gross, then net in the ink bar.
    story += [_label("payslip.this_period", locale), Spacer(1, 1.8 * mm),
              _rows([(t("payslip.period", locale), period),
                     (t("payslip.issued_on", locale), data.get("issued_on")),
                     (t("payslip.gross", locale), _money(data.get("gross"), locale))]),
              Spacer(1, 3 * mm), Rule(WIDTH / 2, 1.2 * mm, LIME)]
    net = Table([[Tracked(t("payslip.net", locale).upper(), MONO_MEDIUM, 7.5, PAPER, tracking=1.05, leading=9),
                  Paragraph(_text(_money(data.get("net"), locale)), NET_AMT)]],
                colWidths=[30 * mm, WIDTH / 2 - 30 * mm], hAlign="LEFT")
    net.setStyle(TableStyle([*_FLAT, ("BACKGROUND", (0, 0), (-1, -1), INK), ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                             ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
                             ("LEFTPADDING", (0, 0), (0, 0), 4 * mm), ("RIGHTPADDING", (-1, 0), (-1, 0), 4 * mm)]))
    story += [net, Spacer(1, 9 * mm)]

    # Year to date.
    story += [_label("payslip.ytd", locale), Spacer(1, 1.8 * mm),
              _rows([(t("payslip.ytd_gross", locale), _money(data.get("ytd_gross"), locale)),
                     (t("payslip.ytd_net", locale), _money(data.get("ytd_net"), locale))])]

    doc.build(story, canvasmaker=_canvas_class(locale))
    return target.getvalue()
