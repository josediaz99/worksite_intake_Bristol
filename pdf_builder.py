"""
pdf_builder.py
report lab PDF layout, takes didck base64 sig returns bytes
"""
import io
import base64
import uuid
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Image, HRFlowable, Table, TableStyle
)


def build_pdf(form_data: dict, signature_b64: str) -> bytes:
    """
    Build a payment record PDF in memory.
    Returns raw PDF bytes — never touches disk.
    """
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch,
        rightMargin=0.85 * inch,
    )

    styles   = getSampleStyleSheet()
    story    = []
    ref_id   = str(uuid.uuid4())[:8].upper()
    ts       = datetime.now().strftime('%d %B %Y at %H:%M')

    # ── Header ────────────────────────────────────────────────
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=18,
        spaceAfter=4,
        textColor=colors.HexColor('#1e3a5f')
    )
    sub_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#666666'),
        spaceAfter=12
    )

    story.append(Paragraph("Worksite Payment Record", title_style))
    story.append(Paragraph(f"Reference: {ref_id} &nbsp;&nbsp;|&nbsp;&nbsp; Generated: {ts}", sub_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1e3a5f')))
    story.append(Spacer(1, 16))

    # ── Section: Worker & Job ─────────────────────────────────
    story.append(_section_heading("Worker & Job Information", styles))

    worker_fields = {k: v for k, v in form_data.items()
                     if k in ["Worker Name", "Contact", "Job Description", "Date of Work"]}
    story.append(_data_table(worker_fields))
    story.append(Spacer(1, 14))

    # ── Section: Payment ──────────────────────────────────────
    story.append(_section_heading("Payment Breakdown", styles))

    payment_fields = {k: v for k, v in form_data.items()
                      if k in ["Hours Worked", "Hourly Rate", "Total Payment", "Authorised By"]}
    story.append(_data_table(payment_fields))
    story.append(Spacer(1, 20))

    # ── Section: Signature ────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
    story.append(Spacer(1, 12))
    story.append(_section_heading("Authorised Signature", styles))

    sig_bytes = base64.b64decode(signature_b64.split(",")[1])
    sig_img   = Image(io.BytesIO(sig_bytes), width=2.8 * inch, height=1.0 * inch)
    sig_img.hAlign = 'LEFT'
    story.append(sig_img)
    story.append(Spacer(1, 6))

    sig_line_style = ParagraphStyle(
        'SigLine',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888')
    )
    story.append(Paragraph(
        f"Signed digitally on {ts} &nbsp; | &nbsp; Ref: {ref_id}",
        sig_line_style
    ))

    # ── Build ─────────────────────────────────────────────────
    doc.build(story)
    return buffer.getvalue()


# ── Helpers ───────────────────────────────────────────────────

def _section_heading(text: str, styles) -> Paragraph:
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#1e3a5f'),
        spaceAfter=8,
        spaceBefore=4,
    )
    return Paragraph(text, heading_style)


def _data_table(fields: dict) -> Table:
    """Render a two-column label/value table."""
    label_style = ParagraphStyle(
        'Label',
        fontName='Helvetica-Bold',
        fontSize=9,
        textColor=colors.HexColor('#555555')
    )
    value_style = ParagraphStyle(
        'Value',
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#111111'),
        leading=14
    )

    data = [
        [
            Paragraph(label, label_style),
            Paragraph(str(value), value_style)
        ]
        for label, value in fields.items()
    ]

    table = Table(data, colWidths=[1.8 * inch, 4.8 * inch])
    table.setStyle(TableStyle([
        ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.HexColor('#f9f9f9'), colors.white]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#eeeeee')),
    ]))
    return table