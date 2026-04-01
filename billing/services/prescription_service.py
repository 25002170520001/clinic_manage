import io
import logging
from datetime import date

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)


def _render_pdf_bytes_with_reportlab(prescription):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = 800
    left = 50

    doctor_name = prescription.doctor.user.get_full_name() or prescription.doctor.user.username
    patient_name = prescription.patient.get_full_name() or prescription.patient.username

    header_lines = [
        "PulseCare Clinic Prescription",
        f"Date: {date.today().isoformat()}",
        f"Doctor: Dr. {doctor_name}",
        f"Patient: {patient_name}",
        f"Appointment ID: {prescription.appointment_id}",
        "",
        f"Symptoms: {prescription.symptoms or '-'}",
        f"Diagnosis: {prescription.diagnosis or '-'}",
        f"Notes: {prescription.notes or '-'}",
        f"Follow-up: {prescription.follow_up_date or '-'}",
        "",
        "Medicines:",
    ]
    for line in header_lines:
        pdf.drawString(left, y, line)
        y -= 20
        if y < 60:
            pdf.showPage()
            y = 800

    medicine_items = list(prescription.medicine_items.all())
    if medicine_items:
        for index, item in enumerate(medicine_items, start=1):
            details = (
                f"{index}. {item.medicine_name} | Dose: {item.dose or '-'} | "
                f"{item.times_per_day}x/day | {item.duration_days} days | "
                f"{item.quantity_tablets} tabs | {item.get_timing_display()} | "
                f"{item.instruction or '-'}"
            )
            pdf.drawString(left, y, details[:110])
            y -= 20
            if y < 60:
                pdf.showPage()
                y = 800
    else:
        pdf.drawString(left, y, prescription.medicines or "-")
        y -= 20

    pdf.showPage()
    pdf.save()
    value = buffer.getvalue()
    buffer.close()
    return value


class PrescriptionService:
    @staticmethod
    def build_prescription_pdf(prescription):
        try:
            return _render_pdf_bytes_with_reportlab(prescription)
        except Exception as exc:
            logger.warning("Prescription PDF generation failed for id=%s: %s", prescription.id, exc)
            return None

    @staticmethod
    def email_prescription_to_patient(prescription):
        patient_email = prescription.patient.email
        if not patient_email:
            logger.info("Skipping prescription email id=%s: patient has no email", prescription.id)
            return False

        pdf_bytes = PrescriptionService.build_prescription_pdf(prescription)
        if not pdf_bytes:
            logger.warning("Skipping prescription email id=%s: PDF bytes not available", prescription.id)
            return False
        subject = f"Prescription - Appointment #{prescription.appointment_id}"
        body = "Your prescription is attached as PDF."
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@pulsecare.local")

        mail = EmailMessage(subject=subject, body=body, from_email=from_email, to=[patient_email])
        mail.attach(
            f"prescription_{prescription.id}.pdf",
            pdf_bytes,
            "application/pdf",
        )
        try:
            sent_count = mail.send(fail_silently=False)
            if sent_count < 1:
                logger.warning("Prescription email send returned 0 for id=%s", prescription.id)
                return False
            return True
        except Exception as exc:
            logger.exception("Prescription email failed for id=%s: %s", prescription.id, exc)
            return False
