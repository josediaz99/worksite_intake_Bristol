"""
pdf_filler.py
Fills Bristol_Service_Call_Interactive.pdf with form data and signature image overlays,
then optionally encrypts the result with AES-256 using PDF_PASSWORD env var.
"""
import base64
import io
import os
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

_PDF_TEMPLATE = Path(__file__).parent / "Bristol_Service_Call_Interactive.pdf"

# (x, y, width, height) in PDF points — derived from AcroForm /Rect annotations
_CUST_SIG_RECT = (38.0, 55.0, 263.0, 32.0)   # cust_sig field: [38, 55, 301, 87]
_HD_SIG_RECT   = (311.0, 55.0, 263.0, 32.0)   # hd_sig field:   [311, 55, 574, 87]

# Checkbox export values used in this PDF
_CHECKBOX_ON  = "/Yes"
_CHECKBOX_OFF = "/Off"


def fill_service_report(fields: dict, cust_sig_b64: str, hd_sig_b64: str) -> bytes:
    """
    Fill the Bristol service call PDF with form data and PNG signature overlays.

    Args:
        fields:       dict mapping AcroForm field names → string values.
                      Use _CHECKBOX_ON / _CHECKBOX_OFF for eq_yes / eq_no.
        cust_sig_b64: PNG data URL for the customer signature.
        hd_sig_b64:   PNG data URL for the hose doctor signature.

    Returns:
        PDF bytes, AES-256 encrypted when PDF_PASSWORD env var is set.
    """
    reader = PdfReader(str(_PDF_TEMPLATE))
    writer = PdfWriter()
    writer.append(reader)

    # Ask viewers to regenerate appearance streams so filled text is visible
    root = writer._root_object
    if "/AcroForm" in root:
        root["/AcroForm"].update(
            {NameObject("/NeedAppearances"): BooleanObject(True)}
        )

    # Signature positions are handled as image overlays — skip them here
    fill_fields = {k: v for k, v in fields.items() if k not in ("cust_sig", "hd_sig")}
    writer.update_page_form_field_values(writer.pages[0], fill_fields)

    # Build a one-page reportlab canvas with just the two signature images
    page    = reader.pages[0]
    page_w  = float(page.mediabox.width)
    page_h  = float(page.mediabox.height)

    overlay_buf = io.BytesIO()
    c = rl_canvas.Canvas(overlay_buf, pagesize=(page_w, page_h))

    def _stamp(b64_url: str, x: float, y: float, w: float, h: float) -> None:
        raw = base64.b64decode(b64_url.split(",", 1)[1])
        img = ImageReader(io.BytesIO(raw))
        # Small inset so the image does not bleed past the field border
        c.drawImage(img, x + 2, y + 2, width=w - 4, height=h - 4,
                    preserveAspectRatio=True, mask="auto")

    _stamp(cust_sig_b64, *_CUST_SIG_RECT)
    _stamp(hd_sig_b64,   *_HD_SIG_RECT)
    c.save()
    overlay_buf.seek(0)

    # merge_page appends overlay content after the form content → renders on top
    overlay_page = PdfReader(overlay_buf).pages[0]
    writer.pages[0].merge_page(overlay_page)

    # Encrypt with AES-256 when PDF_PASSWORD is configured
    password = os.getenv("PDF_PASSWORD", "").strip()
    if password:
        writer.encrypt(password)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
