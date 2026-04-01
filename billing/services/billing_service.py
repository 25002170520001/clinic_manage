from decimal import Decimal

import io
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from appointments.models import Appointment

from billing.models import Bill, Prescription
from billing.models import NotificationDelivery
from billing.services.prescription_service import PrescriptionService

logger = logging.getLogger(__name__)


class BillingService:
    NEW_PATIENT_FEE = Decimal("100.00")
    OLD_PATIENT_FEE = Decimal("80.00")

    @staticmethod
    def _next_bill_number():
        today = timezone.localdate().strftime("%Y%m%d")
        prefix = f"BILL-{today}-"
        last = Bill.objects.filter(bill_number__startswith=prefix).order_by("-bill_number").first()
        if not last:
            seq = 1
        else:
            try:
                seq = int(last.bill_number.split("-")[-1]) + 1
            except Exception:
                seq = 1
        return f"{prefix}{seq:04d}"

    @staticmethod
    def _is_new_patient(patient, current_appointment=None):
        had_old_appointment = Appointment.objects.filter(patient=patient, status="completed")
        if current_appointment:
            had_old_appointment = had_old_appointment.exclude(id=current_appointment.id)
        had_old_appointment = had_old_appointment.exists()

        had_prescription = Prescription.objects.filter(patient=patient)
        if current_appointment:
            had_prescription = had_prescription.exclude(appointment=current_appointment)
        had_prescription = had_prescription.exists()

        return not had_old_appointment and not had_prescription

    @staticmethod
    def create_or_get_bill_for_appointment(appointment):
        if not appointment:
            return None, False
        existing = Bill.objects.filter(appointment=appointment).first()
        if existing:
            return existing, False

        is_new = BillingService._is_new_patient(appointment.patient, current_appointment=appointment)
        consultation_fee = BillingService.NEW_PATIENT_FEE if is_new else BillingService.OLD_PATIENT_FEE
        bill = Bill.objects.create(
            bill_number=BillingService._next_bill_number(),
            patient=appointment.patient,
            doctor=appointment.doctor,
            appointment=appointment,
            consultation_fee=consultation_fee,
            medicine_cost=Decimal("0.00"),
            other_charges=Decimal("0.00"),
            discount=Decimal("0.00"),
            total_amount=consultation_fee,
            status="pending",
            notes="New patient fee applied (INR 100)" if is_new else "Returning patient fee applied (INR 80)",
        )
        return bill, True

    @staticmethod
    def build_bill_pdf(bill):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
        except Exception as exc:
            logger.warning("Bill PDF generation library unavailable for bill=%s: %s", bill.id, exc)
            return None

        try:
            buffer = io.BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=A4)
            y = 800
            left = 50

            patient_name = bill.patient.get_full_name() or bill.patient.username
            doctor_name = bill.doctor.user.get_full_name() or bill.doctor.user.username

            lines = [
                "Family Health Care - Paid Bill Receipt",
                f"Bill Number: {bill.bill_number}",
                f"Date: {timezone.localdate().isoformat()}",
                f"Patient: {patient_name}",
                f"Doctor: Dr. {doctor_name}",
                f"Appointment ID: {bill.appointment_id or '-'}",
                "",
                f"Consultation Fee: INR {bill.consultation_fee}",
                f"Medicine Cost: INR {bill.medicine_cost}",
                f"Other Charges: INR {bill.other_charges}",
                f"Discount: INR {bill.discount}",
                f"Total Paid: INR {bill.total_amount}",
                f"Status: {bill.get_status_display()}",
            ]

            for line in lines:
                pdf.drawString(left, y, line)
                y -= 20
                if y < 60:
                    pdf.showPage()
                    y = 800

            pdf.showPage()
            pdf.save()
            value = buffer.getvalue()
            buffer.close()
            return value
        except Exception as exc:
            logger.exception("Bill PDF generation failed for bill=%s: %s", bill.id, exc)
            return None

    @staticmethod
    def _get_prescription_for_bill(bill):
        if bill.appointment_id:
            return (
                Prescription.objects.filter(appointment_id=bill.appointment_id)
                .select_related("patient", "doctor__user")
                .order_by("-created_at")
                .first()
            )
        return (
            Prescription.objects.filter(patient=bill.patient, doctor=bill.doctor)
            .select_related("patient", "doctor__user")
            .order_by("-created_at")
            .first()
        )

    @staticmethod
    def email_bill_and_prescription(bill):
        patient_email = bill.patient.email
        if not patient_email:
            return False, "Patient email is missing."

        bill_pdf = BillingService.build_bill_pdf(bill)
        if not bill_pdf:
            return False, "Bill PDF could not be generated."

        prescription = BillingService._get_prescription_for_bill(bill)
        prescription_pdf = None
        if prescription:
            prescription_pdf = PrescriptionService.build_prescription_pdf(prescription)

        subject = f"Bill & Prescription - {bill.bill_number}"
        body = (
            "Your paid bill is attached.\n"
            "Prescription is attached if available.\n"
            "Thank you for visiting Family Health Care."
        )
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@familyhealthcare.local")

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=from_email,
            to=[patient_email],
        )
        email.attach(f"{bill.bill_number}.pdf", bill_pdf, "application/pdf")

        if prescription_pdf:
            email.attach(f"prescription_{prescription.id}.pdf", prescription_pdf, "application/pdf")

        try:
            sent_count = email.send(fail_silently=False)
            if sent_count < 1:
                NotificationDelivery.objects.create(
                    channel="email",
                    status="failed",
                    recipient=patient_email,
                    subject=subject,
                    message=body,
                    error="Email send returned 0",
                    bill=bill,
                    prescription=prescription if prescription_pdf else None,
                )
                return False, "Email send returned 0."

            update_fields = ["email_sent", "emailed_at", "email_error", "updated_at"]
            bill.email_sent = True
            bill.emailed_at = timezone.now()
            bill.email_error = ""
            bill.save(update_fields=update_fields)

            if prescription and prescription_pdf:
                prescription.email_sent = True
                prescription.emailed_at = timezone.now()
                prescription.save(update_fields=["email_sent", "emailed_at", "updated_at"])

            NotificationDelivery.objects.create(
                channel="email",
                status="sent",
                recipient=patient_email,
                subject=subject,
                message=body,
                bill=bill,
                prescription=prescription if prescription_pdf else None,
            )
            return True, ""
        except Exception as exc:
            logger.exception("Email send failed for bill=%s: %s", bill.id, exc)
            bill.email_sent = False
            bill.email_error = str(exc)
            bill.save(update_fields=["email_sent", "email_error", "updated_at"])
            NotificationDelivery.objects.create(
                channel="email",
                status="failed",
                recipient=patient_email,
                subject=subject,
                message=body,
                error=str(exc),
                bill=bill,
                prescription=prescription if prescription_pdf else None,
            )
            return False, str(exc)
