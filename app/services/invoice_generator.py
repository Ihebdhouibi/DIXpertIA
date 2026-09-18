from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
from datetime import datetime

# Map status values to human-readable labels
STATUS_MAP = {
    "brouillon": "Draft",
    "envoyee": "Sent",
    "payee": "Paid",
    "en_retard": "Overdue",
    "annulee": "Cancelled",
    "Sent": "Sent",
    "Paid": "Paid",
    "Overdue": "Overdue",
    "Draft": "Draft",
}

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
    invoice_id = invoice_data.get('invoice_id', '')
    client = invoice_data.get('client', '')
    client_address = invoice_data.get('client_address', 'N/A')
    date_issued = invoice_data.get('date_issued', '')
    due_date = invoice_data.get('due_date', '')
    status_raw = invoice_data.get('status', 'Sent')
    status = STATUS_MAP.get(status_raw, status_raw)
    items = invoice_data.get('items', [])
    subtotal = invoice_data.get('subtotal', 0)
    total = invoice_data.get('total', 0)

    story = []

    # --- Company header ---
    story.append(Paragraph("DIXpertIA", title_style))
    story.append(Paragraph("Enterprise IT Solutions & Infrastructure Services", subtitle_style))
    story.append(Spacer(1, 0.2*inch))

    # --- Invoice title, number, date ---
    inv_title = Paragraph("INVOICE", title_style)
    inv_number = Paragraph(f"<b>{invoice_id}</b>", header_style)
    inv_date = Paragraph(f"Date: {date_issued}", header_style)

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
    billed_to = Paragraph("<b>BILLED TO:</b>", label_style)
    client_name = Paragraph(client, value_style)
    address_lines = client_address.split('\n') if '\n' in client_address else [client_address]
    client_addr = Paragraph("<br/>".join(address_lines), value_style)

    due_label = Paragraph("<b>DUE DATE:</b>", label_style)
    due_value = Paragraph(due_date, value_style)
    status_label = Paragraph("<b>Status:</b>", label_style)
    status_value = Paragraph(status, status_style)

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
            [Paragraph("<b>Description</b>", header_style),
             Paragraph("<b>Qty</b>", header_style),
             Paragraph("<b>Price</b>", header_style),
             Paragraph("<b>Total</b>", header_style)]
        ]
        for item in items:
            desc = Paragraph(item.get('description', ''), value_style)
            qty = Paragraph(str(item.get('qty', 0)), value_style)
            price = Paragraph(f"${item.get('price', 0):.2f}", value_style)
            total_item = Paragraph(f"${item.get('total', 0):.2f}", value_style)
            item_table_data.append([desc, qty, price, total_item])

        # Add subtotal and total
        item_table_data.append(
            ["", "", Paragraph("<b>Subtotal:</b>", label_style), Paragraph(f"${subtotal:.2f}", total_style)]
        )
        item_table_data.append(
            ["", "", Paragraph("<b>Total Due:</b>", label_style), Paragraph(f"${total:.2f}", total_style)]
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
            ('BACKGROUND', (0,-2), (-1,-1), colors.HexColor('#e8eef5')),
            ('FONTNAME', (0,-2), (-1,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,-2), (-1,-1), colors.HexColor('#1a2a6c')),
            ('FONTSIZE', (0,-2), (-1,-1), 10),
        ]))
        story.append(item_table)
    else:
        story.append(Paragraph("No items.", value_style))

    story.append(Spacer(1, 0.3*inch))

    # --- Footer ---
    footer_text = """
    <font size=8 color=#999999>
    This invoice is automatically generated by DIXpertIA.<br/>
    For any questions, please contact billing@dixpertia.com
    </font>
    """
    story.append(Paragraph(footer_text, styles['Normal']))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        f"<font size=8 color=#999999>Generated on {datetime.now().strftime('%d %b %Y, %H:%M')}</font>",
        styles['Normal']
    ))

    doc.build(story)

    if output_path is None:
        buffer.seek(0)
        return buffer.getvalue()
    return output_path
