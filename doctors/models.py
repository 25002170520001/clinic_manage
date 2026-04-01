
from django.db import models
from django.conf import settings


class Doctor(models.Model):
    """Doctor profile model"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.CharField(max_length=100)
    qualification = models.CharField(max_length=200)
    experience = models.PositiveIntegerField(default=0)  # years
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} - {self.specialization}"

    def get_full_name(self):
        return f"Dr. {self.user.get_full_name()}"

