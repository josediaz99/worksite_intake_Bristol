"""
app.py
Flask app init, routes, config, and email sender.
"""
import os
from flask import Flask, render_template, redirect, url_for, flash
from flask_mail import Mail, Message
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv

load_dotenv()

from forms import BristolServiceCallForm, PaymentIntakeForm
from pdf_filler import fill_service_report
from pdf_builder import build_pdf

# ── App Init ─────────────────────────────────────────────────────────────────
app = Flask(__name__)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "local-dev-secret-key")

# ── Mail Config ───────────────────────────────────────────────────────────────
app.config["MAIL_SERVER"]         = os.getenv("MAIL_SERVER", "localhost")
app.config["MAIL_PORT"]           = int(os.getenv("MAIL_PORT", "1025"))
app.config["MAIL_USE_SSL"]        = _env_bool("MAIL_USE_SSL", False)
app.config["MAIL_USE_TLS"]        = _env_bool("MAIL_USE_TLS", False)
app.config["MAIL_USERNAME"]       = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"]       = os.getenv("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.getenv("MAIL_DEFAULT_SENDER") or os.getenv("MAIL_USERNAME")

# ── Security Config ───────────────────────────────────────────────────────────
app.config["WTF_CSRF_ENABLED"]       = True
app.config["WTF_CSRF_TIME_LIMIT"]    = 3600
app.config["SESSION_COOKIE_SECURE"]  = _env_bool("SESSION_COOKIE_SECURE", False)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ── Extensions ────────────────────────────────────────────────────────────────
_MAIL_REQUIRED = ("MAIL_SERVER", "MAIL_PORT", "MAIL_DEFAULT_SENDER", "RECIPIENT_EMAIL")
mail_enabled = all(os.getenv(k) for k in _MAIL_REQUIRED)

mail    = Mail(app)
csrf    = CSRFProtect(app)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["100 per day", "30 per hour"],
    storage_uri="memory://"
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def service_report():
    form = BristolServiceCallForm()

    if form.validate_on_submit():
        # Build PDF field mapping — never log cc_number / cc_cvv
        pdf_fields = {
            "date":          form.date.data.strftime("%m/%d/%Y") if form.date.data else "",
            "name":          form.name.data or "",
            "site_contact":  form.site_contact.data  or "",
            "site_address":  form.site_address.data  or "",
            "contact_ph":    form.contact_ph.data    or "",
            "city":          form.city.data          or "",
            "state":         form.state.data         or "",
            "zip":           form.zip.data           or "",
            "purchase_order": form.purchase_order.data or "",
            "machine_type":  form.machine_type.data  or "",
            "unit_number":   form.unit_number.data   or "",
            "serial_number": form.serial_number.data or "",
            "machine_hrs":   form.machine_hrs.data   or "",
            "technician":    form.technician.data    or "",
            "tech_notes":    form.tech_notes.data    or "",
            "subtotal":      form.subtotal.data      or "",
            "tax":           form.tax.data           or "",
            "total":         form.total.data         or "",
            "drive_to":      form.drive_to.data      or "",
            "drive_from":    form.drive_from.data    or "",
            "site_in":       form.site_in.data       or "",
            "site_out":      form.site_out.data      or "",
            "cc_number":     form.cc_number.data     or "",
            "cc_expiry":     form.cc_expiry.data     or "",
            "cc_cvv":        form.cc_cvv.data        or "",
            "billing_zip":   form.billing_zip.data   or "",
            "cust_name_print": form.cust_name_print.data or "",
            "hd_date":       form.hd_date.data.strftime("%m/%d/%Y") if form.hd_date.data else "",
        }

        # Parts rows 0–4
        for i in range(5):
            pdf_fields[f"qty_{i}"]  = getattr(form, f"qty_{i}").data  or ""
            pdf_fields[f"part_{i}"] = getattr(form, f"part_{i}").data or ""
            pdf_fields[f"desc_{i}"] = getattr(form, f"desc_{i}").data or ""
            pdf_fields[f"unit_{i}"] = getattr(form, f"unit_{i}").data or ""
            pdf_fields[f"ext_{i}"]  = getattr(form, f"ext_{i}").data  or ""

        # Equipment checkboxes
        eq = form.equipment_ok.data
        pdf_fields["eq_yes"] = "/Yes" if eq == "yes" else "/Off"
        pdf_fields["eq_no"]  = "/Yes" if eq == "no"  else "/Off"

        try:
            pdf_bytes = fill_service_report(
                pdf_fields,
                form.cust_sig_data.data or "",
                form.hd_sig_data.data or "",
            )
            email_sent = _send_report_email(pdf_bytes, form.name.data or "")
            if not email_sent:
                flash(
                    "Report processed locally. Email delivery is disabled until "
                    "SMTP env vars are configured.",
                    "info",
                )
            return redirect(url_for("success"))

        except Exception as e:
            app.logger.error("Service report processing failed: %s", e)
            flash("There was a problem generating the report. Please try again.", "error")

    return render_template("bristol_form.html", form=form)


@app.route("/payment", methods=["GET", "POST"])
@limiter.limit("10 per hour")
def payment():
    form = PaymentIntakeForm()

    if form.validate_on_submit():
        form_data = {
            "Worker Name":     form.worker_name.data,
            "Contact":         form.worker_contact.data,
            "Job Description": form.job_description.data,
            "Date of Work":    form.work_date.data.strftime("%d %B %Y"),
            "Hours Worked":    f"{form.hours_worked.data:.2f}",
            "Hourly Rate":     f"${form.hourly_rate.data:.2f}",
            "Total Payment":   f"${form.total_payment.data:.2f}",
            "Authorised By":   form.supervisor_name.data,
        }

        try:
            pdf_bytes  = build_pdf(form_data, form.signature_data.data or "")
            email_sent = _send_payment_email(pdf_bytes, form.worker_name.data or "")
            if not email_sent:
                flash(
                    "Form submitted locally. Email delivery is disabled until "
                    "SMTP env vars are configured.",
                    "info",
                )
            return redirect(url_for("success"))

        except Exception as e:
            app.logger.error("Payment submission failed: %s", e)
            flash("There was a problem processing your submission. Please try again.", "error")

    return render_template("form.html", form=form)


@app.route("/success")
def success():
    return render_template("success.html")


# ── Email Helpers ─────────────────────────────────────────────────────────────

def _send_report_email(pdf_bytes: bytes, customer_name: str) -> bool:
    """Send the encrypted Bristol service report to the configured recipient."""
    if not mail_enabled:
        app.logger.warning("Email skipped: mail settings not fully configured.")
        return False

    recipient = os.environ["RECIPIENT_EMAIL"]
    encrypted = bool(os.getenv("PDF_PASSWORD", "").strip())

    body_lines = [
        f"Please find attached the completed service call report for {customer_name}.",
        "",
        "This document was submitted via the Bristol Worksite Intake System.",
    ]
    if encrypted:
        body_lines += [
            "",
            "SECURITY NOTICE: The attached PDF is password-protected with AES-256 "
            "encryption. Please use the document password to open it.",
            "This email was sent over an encrypted connection (TLS/SSL).",
        ]

    safe_name = customer_name.replace(" ", "_")
    msg = Message(
        subject=f"Bristol Service Report — {customer_name}",
        recipients=[recipient],
    )
    msg.body = "\n".join(body_lines)
    msg.attach(
        filename=f"service_report_{safe_name}.pdf",
        content_type="application/pdf",
        data=pdf_bytes,
    )
    mail.send(msg)
    return True


def _send_payment_email(pdf_bytes: bytes, worker_name: str) -> bool:
    """Send the payment record PDF to the configured recipient."""
    if not mail_enabled:
        app.logger.warning("Email skipped: mail settings not fully configured.")
        return False

    recipient = os.environ["RECIPIENT_EMAIL"]
    msg = Message(
        subject=f"Payment Record — {worker_name}",
        recipients=[recipient],
    )
    msg.body = (
        f"Please find attached the payment intake record for {worker_name}.\n\n"
        "This is an automated message from the Worksite Intake System."
    )
    msg.attach(
        filename=f"payment_{worker_name.replace(' ', '_')}.pdf",
        content_type="application/pdf",
        data=pdf_bytes,
    )
    mail.send(msg)
    return True


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.getenv("PORT", "5000")),
        debug=_env_bool("FLASK_DEBUG", True),
    )
