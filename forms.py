"""
forms.py
All field definitions, validators, and custom cross-field validation.
"""
from datetime import date
from flask_wtf import FlaskForm
from wtforms import (
    StringField, DecimalField, DateField,
    TextAreaField, HiddenField, SelectField
)
from wtforms.validators import (
    DataRequired, Length, NumberRange, Optional,
    ValidationError, Regexp
)


# ── Shared signature validator ───────────────────────────────────────────────

def _check_sig_data(field) -> None:
    """Raise ValidationError when a signature hidden field is empty or blank."""
    if not field.data or not field.data.startswith("data:image/png;base64,"):
        raise ValidationError("Invalid signature format.")
    b64_part = field.data.split(",", 1)[1]
    if len(b64_part) < 5000:
        raise ValidationError("Signature appears to be empty. Please sign.")


# ── Payment intake form (original) ──────────────────────────────────────────

class PaymentIntakeForm(FlaskForm):

    worker_name = StringField(
        "Worker Full Name",
        validators=[
            DataRequired(message="Worker name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
            Regexp(
                r"^[A-Za-z\s'\-\.]+$",
                message="Name may only contain letters, spaces, hyphens, apostrophes, and periods."
            )
        ],
        render_kw={"placeholder": "Full legal name", "autocomplete": "name"}
    )

    worker_contact = StringField(
        "Contact (Phone or Email)",
        validators=[
            DataRequired(message="A contact number or email is required."),
            Length(min=7, max=100, message="Contact must be between 7 and 100 characters.")
        ],
        render_kw={"placeholder": "e.g. 07700 900000 or worker@email.com"}
    )

    job_description = TextAreaField(
        "Job / Work Description",
        validators=[
            DataRequired(message="Job description is required."),
            Length(min=10, max=1000, message="Description must be between 10 and 1000 characters.")
        ],
        render_kw={"placeholder": "Describe the work carried out", "rows": 4}
    )

    work_date = DateField(
        "Date of Work",
        validators=[DataRequired(message="Date of work is required.")]
    )

    hours_worked = DecimalField(
        "Hours Worked",
        places=2,
        validators=[
            DataRequired(message="Hours worked is required."),
            NumberRange(min=0.1, max=24, message="Hours must be between 0.1 and 24.")
        ],
        render_kw={"inputmode": "decimal", "placeholder": "e.g. 8.5"}
    )

    hourly_rate = DecimalField(
        "Hourly Rate ($)",
        places=2,
        validators=[
            DataRequired(message="Hourly rate is required."),
            NumberRange(min=0.01, max=9999.99, message="Rate must be between $0.01 and $9,999.99.")
        ],
        render_kw={"inputmode": "decimal", "placeholder": "e.g. 25.00"}
    )

    total_payment = DecimalField(
        "Total Payment ($)",
        places=2,
        validators=[
            DataRequired(message="Total payment amount is required."),
            NumberRange(min=0.01, max=999999.99, message="Total must be between $0.01 and $999,999.99.")
        ],
        render_kw={"inputmode": "decimal", "placeholder": "e.g. 212.50"}
    )

    supervisor_name = StringField(
        "Supervisor / Authoriser Name",
        validators=[
            DataRequired(message="Supervisor name is required."),
            Length(min=2, max=100, message="Name must be between 2 and 100 characters."),
            Regexp(
                r"^[A-Za-z\s'\-\.]+$",
                message="Name may only contain letters, spaces, hyphens, apostrophes, and periods."
            )
        ],
        render_kw={"placeholder": "Supervisor or site manager"}
    )

    signature_data = HiddenField(
        "Signature",
        validators=[DataRequired(message="A signature is required.")]
    )

    def validate_work_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Work date cannot be in the future.")

    def validate_total_payment(self, field):
        if self.hours_worked.data and self.hourly_rate.data and field.data:
            expected = float(self.hours_worked.data) * float(self.hourly_rate.data)
            actual   = float(field.data)
            if abs(expected - actual) > 1.00:
                raise ValidationError(
                    f"Total payment (${actual:.2f}) doesn't match "
                    f"hours × rate (${expected:.2f}). Please check."
                )

    def validate_signature_data(self, field):
        _check_sig_data(field)


# ── Bristol Service Call form ────────────────────────────────────────────────

class BristolServiceCallForm(FlaskForm):

    # ── Job Information ──────────────────────────────────────────
    date = DateField(
        "Service Date",
        validators=[DataRequired(message="Service date is required.")]
    )
    name = StringField(
        "Customer Name",
        validators=[
            DataRequired(message="Customer name is required."),
            Length(min=2, max=100)
        ],
        render_kw={"placeholder": "Full name", "autocomplete": "name"}
    )
    site_contact = StringField(
        "Site Contact",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Contact person on site"}
    )
    site_address = StringField(
        "Site Address",
        validators=[Optional(), Length(max=200)],
        render_kw={"placeholder": "Street address", "autocomplete": "street-address"}
    )
    contact_ph = StringField(
        "Phone",
        validators=[Optional(), Length(max=30)],
        render_kw={"placeholder": "Phone number", "autocomplete": "tel", "inputmode": "tel"}
    )
    city = StringField(
        "City",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "City", "autocomplete": "address-level2"}
    )
    state = StringField(
        "State / Province",
        validators=[Optional(), Length(max=50)],
        render_kw={"placeholder": "State", "autocomplete": "address-level1"}
    )
    zip = StringField(
        "ZIP / Postal Code",
        validators=[Optional(), Length(max=20)],
        render_kw={"placeholder": "ZIP", "autocomplete": "postal-code", "inputmode": "numeric"}
    )
    purchase_order = StringField(
        "Purchase Order #",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "PO number"}
    )

    # ── Machine Information ──────────────────────────────────────
    machine_type  = StringField("Machine Type",  validators=[Optional(), Length(max=100)])
    unit_number   = StringField("Unit #",        validators=[Optional(), Length(max=50)])
    serial_number = StringField("Serial #",      validators=[Optional(), Length(max=100)])
    machine_hrs   = StringField(
        "Machine Hours",
        validators=[Optional(), Length(max=20)],
        render_kw={"inputmode": "numeric"}
    )

    # ── Service Details ──────────────────────────────────────────
    technician = StringField(
        "Technician",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Technician full name"}
    )
    tech_notes = TextAreaField(
        "Technician Notes / Work Performed",
        validators=[Optional(), Length(max=2000)],
        render_kw={"rows": 5, "placeholder": "Describe the work performed, findings, and recommendations"}
    )

    # ── Parts / Materials (5 rows mapped to PDF rows 0–4) ────────
    qty_0  = StringField(validators=[Optional()]); part_0 = StringField(validators=[Optional()])
    desc_0 = StringField(validators=[Optional()]); unit_0 = StringField(validators=[Optional()])
    ext_0  = StringField(validators=[Optional()])

    qty_1  = StringField(validators=[Optional()]); part_1 = StringField(validators=[Optional()])
    desc_1 = StringField(validators=[Optional()]); unit_1 = StringField(validators=[Optional()])
    ext_1  = StringField(validators=[Optional()])

    qty_2  = StringField(validators=[Optional()]); part_2 = StringField(validators=[Optional()])
    desc_2 = StringField(validators=[Optional()]); unit_2 = StringField(validators=[Optional()])
    ext_2  = StringField(validators=[Optional()])

    qty_3  = StringField(validators=[Optional()]); part_3 = StringField(validators=[Optional()])
    desc_3 = StringField(validators=[Optional()]); unit_3 = StringField(validators=[Optional()])
    ext_3  = StringField(validators=[Optional()])

    qty_4  = StringField(validators=[Optional()]); part_4 = StringField(validators=[Optional()])
    desc_4 = StringField(validators=[Optional()]); unit_4 = StringField(validators=[Optional()])
    ext_4  = StringField(validators=[Optional()])

    # ── Time & Travel ────────────────────────────────────────────
    drive_to   = StringField("Drive To",   validators=[Optional(), Length(max=20)],
                             render_kw={"placeholder": "HH:MM"})
    drive_from = StringField("Drive From", validators=[Optional(), Length(max=20)],
                             render_kw={"placeholder": "HH:MM"})
    site_in    = StringField("Site In",    validators=[Optional(), Length(max=20)],
                             render_kw={"placeholder": "HH:MM"})
    site_out   = StringField("Site Out",   validators=[Optional(), Length(max=20)],
                             render_kw={"placeholder": "HH:MM"})

    equipment_ok = SelectField(
        "Equipment Operational After Service?",
        choices=[("", "— select —"), ("yes", "Yes"), ("no", "No")],
        validators=[Optional()]
    )

    # ── Totals ───────────────────────────────────────────────────
    subtotal = StringField("Subtotal", validators=[Optional(), Length(max=20)],
                           render_kw={"placeholder": "0.00", "inputmode": "decimal"})
    tax      = StringField("Tax",      validators=[Optional(), Length(max=20)],
                           render_kw={"placeholder": "0.00", "inputmode": "decimal"})
    total    = StringField("Total",    validators=[Optional(), Length(max=20)],
                           render_kw={"placeholder": "0.00", "inputmode": "decimal"})

    # ── Payment (sensitive — optional, included in encrypted PDF) ─
    cc_number  = StringField("Card Number", validators=[Optional(), Length(max=20)],
                             render_kw={"placeholder": "•••• •••• •••• ••••",
                                        "autocomplete": "off", "inputmode": "numeric"})
    cc_expiry  = StringField("Expiry",      validators=[Optional(), Length(max=10)],
                             render_kw={"placeholder": "MM/YY", "autocomplete": "off"})
    cc_cvv     = StringField("CVV",         validators=[Optional(), Length(max=4)],
                             render_kw={"placeholder": "•••", "autocomplete": "off",
                                        "inputmode": "numeric"})
    billing_zip = StringField("Billing ZIP", validators=[Optional(), Length(max=20)],
                              render_kw={"placeholder": "ZIP", "autocomplete": "off",
                                         "inputmode": "numeric"})

    # ── Signatures ───────────────────────────────────────────────
    cust_sig_data   = HiddenField(validators=[DataRequired(message="Customer signature is required.")])
    cust_name_print = StringField(
        "Customer Printed Name",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "Print full name"}
    )
    hd_sig_data = HiddenField(validators=[DataRequired(message="Hose Doctor signature is required.")])
    hd_date = DateField(
        "Hose Doctor Date",
        format="%Y-%m-%d",
        validators=[Optional()]
    )

    # ── Custom validators ────────────────────────────────────────
    def validate_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Service date cannot be in the future.")

    def validate_cust_sig_data(self, field):
        _check_sig_data(field)

    def validate_hd_sig_data(self, field):
        _check_sig_data(field)
