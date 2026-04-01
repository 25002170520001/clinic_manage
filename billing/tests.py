from django.test import TestCase

from decimal import Decimal

from accounts.models import User
from appointments.models import Appointment
from doctors.models import Doctor

from .models import Bill, ClinicSettings
from .services.billing_service import BillingService
from .services.notification_service import NotificationService


class BillingModelAndServiceTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username="bill_patient",
            password="x",
            role="patient",
            phone="9999999999",
            email="patient@example.com",
        )
        doctor_user = User.objects.create_user(username="bill_doctor", password="x", role="doctor")
        self.doctor = Doctor.objects.create(
            user=doctor_user,
            specialization="General",
            qualification="MBBS",
            experience=3,
        )
        self.appointment = Appointment.objects.create(patient=self.patient, doctor=self.doctor, status="pending")

    def test_bill_calculate_total(self):
        bill = Bill.objects.create(
            bill_number="BILL-TEST-0001",
            patient=self.patient,
            doctor=self.doctor,
            appointment=self.appointment,
            consultation_fee=Decimal("100.00"),
            medicine_cost=Decimal("20.00"),
            other_charges=Decimal("10.00"),
            discount=Decimal("5.00"),
            total_amount=Decimal("125.00"),
        )
        self.assertEqual(bill.calculate_total(), Decimal("125.00"))

    def test_clinic_settings_singleton(self):
        first = ClinicSettings.get_solo()
        second = ClinicSettings.get_solo()
        self.assertEqual(first.id, second.id)
        self.assertFalse(first.sms_enabled)
        self.assertFalse(first.whatsapp_enabled)

    def test_create_or_get_bill_for_appointment_applies_new_patient_fee(self):
        bill, created = BillingService.create_or_get_bill_for_appointment(self.appointment)
        self.assertTrue(created)
        self.assertEqual(bill.consultation_fee, Decimal("100.00"))
        self.assertEqual(bill.status, "pending")

        same_bill, created_again = BillingService.create_or_get_bill_for_appointment(self.appointment)
        self.assertFalse(created_again)
        self.assertEqual(same_bill.id, bill.id)

    def test_notify_payment_documents_can_skip_channels_when_disabled(self):
        bill, _ = BillingService.create_or_get_bill_for_appointment(self.appointment)
        result = NotificationService.notify_payment_documents(
            request=None,
            bill=bill,
            prescription=None,
            send_sms_enabled=False,
            send_whatsapp_enabled=False,
        )
        self.assertFalse(result["sms_sent"])
        self.assertFalse(result["whatsapp_sent"])
        self.assertEqual(result["sms_error"], "Disabled by admin")
        self.assertEqual(result["whatsapp_error"], "Disabled by admin")
