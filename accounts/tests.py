from django.test import TestCase

from .models import PatientProfile, User


class UserModelTests(TestCase):
    def test_role_helper_methods(self):
        patient = User.objects.create_user(username="p1", password="x", role="patient")
        doctor = User.objects.create_user(username="d1", password="x", role="doctor")
        receptionist = User.objects.create_user(username="r1", password="x", role="receptionist")
        admin_user = User.objects.create_user(username="a1", password="x", role="admin")

        self.assertTrue(patient.is_patient())
        self.assertFalse(patient.is_doctor())
        self.assertTrue(doctor.is_doctor())
        self.assertTrue(receptionist.is_receptionist())
        self.assertTrue(admin_user.is_admin_user())

    def test_superuser_is_admin_user(self):
        superuser = User.objects.create_superuser(username="root", password="x", email="root@example.com")
        self.assertTrue(superuser.is_admin_user())


class PatientProfileTests(TestCase):
    def test_patient_profile_string_contains_username(self):
        user = User.objects.create_user(username="patient_profile_user", password="x", role="patient")
        profile = PatientProfile.objects.get(user=user)
        self.assertIn("patient_profile_user", str(profile))
