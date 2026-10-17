from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from datetime import datetime
from xml.sax.saxutils import escape

from app.i18n import CATALOG, DEFAULT_LOCALE, format_amount, format_date, t

# Every word on the PDF comes from app.i18n, in the language passed in
# invoice_data["locale"] - the client's (#135) - and amounts are printed in
# Tunisian dinars. The status is the stored value ("payee"), or "en_retard"
# when derived (#117).
#
# The accountant's processing_status is deliberately NOT printed: it is an
# internal bookkeeping state, and the client has no business seeing whether
# their invoice has been reconciled yet.


def _status_label(raw, locale: str) -> str:
    key = f"pdf.status.{str(raw).lower()}"
    return t(key, locale) if key in CATALOG else str(raw)

def _text(value) -> str:
    """A stored value made safe for a ReportLab Paragraph (#86).

    Paragraph parses its text as markup. A name or a line containing a known
    tag left open, such as "R&D <b>" or "<i>Acme", made the whole PDF fail
    with ValueError, and a closed one silently changed the formatting instead
    of being printed. A NULL address raised TypeError. Missing values become an
    empty string; markup characters are escaped, so stored text prints as is.
    """
    return escape("" if value is None else str(value))


def _draft_watermark(word: str):
    """A large diagonal DRAFT (or BROUILLON) across every page of a draft's PDF (#118).

    A draft has no legal number yet. Its PDF is what the accountant reviews, and
    it must never pass for an invoice if it is printed or forwarded by mistake.
    """
    def draw(canvas, doc):
        canvas.saveState()
        # Sized to the word: BROUILLON is longer than DRAFT.
        canvas.setFont("Helvetica-Bold", 110 if len(word) <= 5 else 80)
        canvas.setFillColor(colors.Color(0.85, 0.15, 0.15, alpha=0.12))
        width, height = A4
        canvas.translate(width / 2, height / 2)
        canvas.rotate(40)
        canvas.drawCentredString(0, -35, word)
        canvas.restoreState()
    return draw


def generate_invoice_pdf(invoice_data: dict, output_path: str = None):
    """
    Generate a professional invoice PDF that matches the frontend modal.
    """
    if output_path is None:
        from io import BytesIO
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                topMargin=1.5*cm, bottomMargin=1.5*cm,
                                leftMargin=1.5*cm, rightMargin=1.5*cm)
    else:
        doc = SimpleDocTemplate(output_path, pagesize=A4,
                                topMargin=1.5*cm, bottomMargin=1.5*cm,
                                leftMargin=1.5*cm, rightMargin=1.5*cm)

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=24,
        textColor=colors.HexColor('#1a2a6c'), alignment=TA_LEFT, spaceAfter=0
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#2c3e50'), alignment=TA_LEFT, spaceAfter=10
    )
    header_style = ParagraphStyle(
        'Header', parent=styles['Normal'], fontSize=10,
        textColor=colors.HexColor('#1a2a6c'), fontName='Helvetica-Bold'
    )
    label_style = ParagraphStyle(
        'Label', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#555555'), fontName='Helvetica-Bold'
    )
    value_style = ParagraphStyle(
        'Value', parent=styles['Normal'], fontSize=9,
        textColor=colors.HexColor('#1a2a6c'), fontName='Helvetica'
    )
    total_style = ParagraphStyle(
        'Total', parent=styles['Normal'], fontSize=12,
        textColor=colors.HexColor('#1a2a6c'), fontName='Helvetica-Bold', alignment=TA_RIGHT
    )
    status_style = ParagraphStyle(
        'Status', parent=styles['Normal'], fontSize=10,
        textColor=colors.HexColor('#1a2a6c'), fontName='Helvetica-Bold'
    )

    # Extract data
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

    story = []

    # --- Company header ---
    story.append(Paragraph("DIXpertIA", title_style))
    story.append(Paragraph(_text(t("pdf.tagline", locale)), subtitle_style))
    story.append(Spacer(1, 0.2*inch))

    # --- Invoice title, number, date ---
    inv_title = Paragraph(_text(t("pdf.invoice", locale)), title_style)
    draft = bool(invoice_data.get('draft'))
    # A draft shows its provisional BR- reference and says the legal number
    # comes on approval - never a predicted number, which could be wrong (#118).
    inv_number = Paragraph(
        f"<b>{invoice_id}</b>"
        + (f"<br/><font size=8>{_text(t('pdf.draft_note', locale))}</font>" if draft else ""),
        header_style,
    )
    inv_date = Paragraph(f"{_text(t('pdf.date', locale))}: {_text(date_issued)}", header_style)

    header_table_data = [
        [inv_title, inv_number],
        ["", inv_date],
    ]
    header_table = Table(header_table_data, colWidths=[4*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('ALIGN', (1,1), (1,1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (0,0), 18),
        ('TEXTCOLOR', (0,0), (0,0), colors.HexColor('#1a2a6c')),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.2*inch))

    # --- Client and Due Date ---
    billed_to = Paragraph(f"<b>{_text(t('pdf.billed_to', locale))}:</b>", label_style)
    client_name = Paragraph(client, value_style)
    client_addr = Paragraph("<br/>".join(_text(line) for line in client_address.split('\n')), value_style)

    due_label = Paragraph(f"<b>{_text(t('pdf.due_date', locale))}:</b>", label_style)
    due_value = Paragraph(_text(due_date), value_style)
    status_label = Paragraph(f"<b>{_text(t('pdf.status', locale))}:</b>", label_style)
    status_value = Paragraph(_text(status), status_style)

    left_data = [[billed_to], [client_name], [client_addr]]
    right_data = [[due_label, due_value],
                  [status_label, status_value]]

    left_table = Table(left_data, colWidths=[3*inch])
    left_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))

    right_table = Table(right_data, colWidths=[1*inch, 2*inch])
    right_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ('ALIGN', (1,1), (1,1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))

    client_table = Table([[left_table, right_table]], colWidths=[4*inch, 3.5*inch])
    client_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (0,0), 0),
        ('RIGHTPADDING', (1,0), (1,0), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(client_table)
    story.append(Spacer(1, 0.2*inch))

    # --- Items table ---
    if items:
        item_table_data = [
            [Paragraph(f"<b>{_text(t('pdf.description', locale))}</b>", header_style),
             Paragraph(f"<b>{_text(t('pdf.qty', locale))}</b>", header_style),
             Paragraph(f"<b>{_text(t('pdf.price', locale))}</b>", header_style),
             Paragraph(f"<b>{_text(t('pdf.total', locale))}</b>", header_style)]
        ]
        for item in items:
            desc = Paragraph(_text(item.get('description')), value_style)
            qty = Paragraph(str(item.get('qty', 0)), value_style)
            # Dinars, not dollars: the PDF printed "$" before #135.
            price = Paragraph(format_amount(item.get('price', 0), locale), value_style)
            total_item = Paragraph(format_amount(item.get('total', 0), locale), value_style)
            item_table_data.append([desc, qty, price, total_item])

        # Add subtotal and total
        item_table_data.append(
            ["", "", Paragraph(f"<b>{_text(t('pdf.subtotal', locale))}:</b>", label_style),
             Paragraph(format_amount(subtotal, locale), total_style)]
        )
        item_table_data.append(
            ["", "", Paragraph(f"<b>{_text(t('pdf.vat', locale))}:</b>", label_style),
             Paragraph(format_amount(round(total - subtotal, 3), locale), total_style)]
        )
        item_table_data.append(
            ["", "", Paragraph(f"<b>{_text(t('pdf.grand_total', locale))}:</b>", label_style),
             Paragraph(format_amount(total, locale), total_style)]
        )

        item_table = Table(item_table_data, colWidths=[3.5*inch, 0.7*inch, 1.0*inch, 1.3*inch])
        item_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (1,0), (1,-1), 'CENTER'),
            ('ALIGN', (2,0), (2,-1), 'RIGHT'),
            ('ALIGN', (3,0), (3,-1), 'RIGHT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a2a6c')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,-3), (-1,-1), colors.HexColor('#e8eef5')),
            ('FONTNAME', (0,-3), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,-3), (-1,-1), colors.HexColor('#1a2a6c')),
            ('FONTSIZE', (0,-3), (-1,-1), 10),
        ]))
        story.append(item_table)
    else:
        story.append(Paragraph(_text(t("pdf.no_items", locale)), value_style))

    story.append(Spacer(1, 0.3*inch))

    # --- Footer ---
    # The catalog's footer carries its own <br/>; nothing in it is user data.
    footer_text = f"<font size=8 color=#999999>{t('pdf.footer', locale)}</font>"
    story.append(Paragraph(footer_text, styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "<font size=8 color=#999999>"
        + _text(t("pdf.generated_on", locale, date=format_date(datetime.now(), locale),
                  time=datetime.now().strftime("%H:%M")))
        + "</font>",
        styles['Normal']
    ))

    if draft:
        watermark = _draft_watermark(t("pdf.draft", locale))
        doc.build(story, onFirstPage=watermark, onLaterPages=watermark)
    else:
        doc.build(story)

    if output_path is None:
        buffer.seek(0)
        return buffer.getvalue()
    return output_path
