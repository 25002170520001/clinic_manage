from django.test import TestCase

from accounts.models import User
from doctors.models import Doctor

from .models import Appointment


class AppointmentModelTests(TestCase):
    def setUp(self):
        self.patient = User.objects.create_user(username="patient1", password="x", role="patient")
        doctor_user = User.objects.create_user(username="doctor1", password="x", role="doctor")
        self.doctor = Doctor.objects.create(
            user=doctor_user,
            specialization="General",
            qualification="MBBS",
            experience=5,
        )

    def test_default_status_and_str(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor)
        self.assertEqual(appt.status, "pending")
        self.assertIn("patient1", str(appt))
        self.assertIn("doctor1", str(appt))

    def test_status_display_class_mapping(self):
        appt = Appointment.objects.create(patient=self.patient, doctor=self.doctor, status="completed")
        self.assertEqual(appt.get_status_display_class(), "success")

        appt.status = "cancelled"
        self.assertEqual(appt.get_status_display_class(), "danger")
