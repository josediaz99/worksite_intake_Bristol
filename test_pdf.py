# test_pdf.py — run with: python test_pdf.py
import base64, os
from pdf_builder import build_pdf

# Tiny valid 1x1 white PNG as a placeholder signature
BLANK_SIG = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI6QAAAABJRU5ErkJggg=="

form_data = {
    "Worker Name":     "Jane Smith",
    "Contact":         "07700 900000",
    "Job Description": "Electrical installation on unit 4B",
    "Date of Work":    "12 June 2025",
    "Hours Worked":    "7.50",
    "Hourly Rate":     "$32.00",
    "Total Payment":   "$240.00",
    "Authorised By":   "Bob Jones",
}

pdf_bytes = build_pdf(form_data, BLANK_SIG)

with open("test_output.pdf", "wb") as f:
    f.write(pdf_bytes)

print(f"PDF generated: {len(pdf_bytes):,} bytes → test_output.pdf")