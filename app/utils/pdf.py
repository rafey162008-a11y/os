"""Invoice PDF generation using ReportLab."""
import io
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, HRFlowable)

from app.utils.helpers import currency


def generate_invoice_pdf(order, store_name='ShopSphere', store_currency='$'):
    """Generate a professional invoice PDF for an order.

    Returns the PDF bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=18 * mm, leftMargin=18 * mm,
                            topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f'Invoice {order.order_number}')

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleX', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#1f2937'))
    h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=13, textColor=colors.HexColor('#374151'))
    small = ParagraphStyle('Small', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#6b7280'))
    normal = styles['Normal']

    elements = []

    # Header
    elements.append(Paragraph(store_name, title_style))
    elements.append(Paragraph(f'Invoice #{order.order_number}', h2))
    elements.append(Paragraph(f'Order date: {order.placed_at.strftime("%d %b %Y, %I:%M %p")}', small))
    elements.append(Paragraph(f'Status: {order.status.replace("_", " ").title()} &nbsp;|&nbsp; '
                              f'Payment: {order.payment_status.replace("_", " ").title()}', small))
    elements.append(HRFlowable(width='100%', thickness=1.2, color=colors.HexColor('#e5e7eb'), spaceAfter=10))

    # Billing info
    addr_lines = (order.shipping_address or 'N/A').split('\n')
    addr_text = '<br/>'.join(addr_lines)
    billing = [
        [Paragraph('<b>Billed To</b>', normal), Paragraph('<b>Store</b>', normal)],
        [Paragraph(order.customer.full_name if order.customer else 'Customer', normal),
         Paragraph(store_name, normal)],
        [Paragraph(addr_text, small), Paragraph(store_name + ' - Online Store', small)],
    ]
    t = Table(billing, colWidths=[90 * mm, 90 * mm])
    t.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 6 * mm))

    # Items table
    data = [['#', 'Product', 'Qty', 'Unit Price', 'Line Total']]
    for i, item in enumerate(order.items, start=1):
        name = item.product_name
        if item.variant_label:
            name += f' ({item.variant_label})'
        data.append([
            str(i), Paragraph(name, normal), str(item.quantity),
            currency(item.unit_price), currency(item.line_total)
        ])

    items_table = Table(data, colWidths=[10 * mm, 85 * mm, 15 * mm, 30 * mm, 40 * mm])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    # Totals
    totals = [
        ['Subtotal', currency(order.subtotal)],
        ['Discount', f'- {currency(order.discount)}'],
        ['Tax', currency(order.tax)],
        ['Shipping', currency(order.shipping_charge)],
        ['Grand Total', currency(order.grand_total)],
    ]
    totals_table = Table(totals, colWidths=[110 * mm, 70 * mm])
    totals_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 4), (-1, 4), 12),
        ('BACKGROUND', (0, 4), (-1, 4), colors.HexColor('#f0f9ff')),
    ]))
    elements.append(totals_table)

    # Payment info
    elements.append(Spacer(1, 6 * mm))
    for payment in order.payments.all():
        elements.append(Paragraph(
            f'Payment: {payment.method_display} - {payment.status.title()} '
            f'({currency(payment.amount)}) ref {payment.payment_reference}', small))

    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph('Thank you for shopping with us!', h2))
    elements.append(Paragraph(
        'This is a system-generated invoice and does not require a signature.', small))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
