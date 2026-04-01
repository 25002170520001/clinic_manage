
from django.db import models
from django.conf import settings
from django.db.models import Q
from doctors.models import Doctor
from appointments.models import Appointment
from .time_utils import filter_today


class QueueToken(models.Model):
    """Token-based queue system for managing patient flow"""
    
    STATUS_CHOICES = [
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('in_consultation', 'In Consultation'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    ]

    token_number = models.PositiveIntegerField()
    token_display = models.CharField(max_length=10)  # e.g., "A-01", "W-02"
    priority = models.PositiveIntegerField(default=1)  # 1 = walk-in, 2 = appointment
    
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='queue_tokens')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='queue_tokens')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='queue_tokens', blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    arrival_time = models.DateTimeField(blank=True, null=True)
    called_time = models.DateTimeField(blank=True, null=True)
    consultation_start_time = models.DateTimeField(blank=True, null=True)
    consultation_end_time = models.DateTimeField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    is_walk_in = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Queue Token'
        verbose_name_plural = 'Queue Tokens'
        ordering = ['-priority', 'token_number', 'created_at']

    def __str__(self):
        return f"{self.token_display} - {self.patient.username} - Dr. {self.doctor.user.username}"

    def get_patients_ahead(self):
        """Calculate number of patients waiting ahead using queue sort rules."""
        return (
            filter_today(
                QueueToken.objects.filter(
                    doctor=self.doctor,
                    status='waiting',
                )
            )
            .filter(
                Q(priority__gt=self.priority)
                | Q(priority=self.priority, token_number__lt=self.token_number)
            )
            .exclude(id=self.id)
            .count()
        )

    def get_estimated_wait_time(self):
        """Calculate estimated wait time in minutes"""
        patients_ahead = self.get_patients_ahead()
        avg_consultation_time = 15  # minutes per patient
        return patients_ahead * avg_consultation_time

    def get_status_display_class(self):
        """Return Bootstrap class for status"""
        status_classes = {
            'waiting': 'warning',
            'called': 'info',
            'in_consultation': 'primary',
            'completed': 'success',
            'missed': 'danger',
            'cancelled': 'secondary',
        }
        return status_classes.get(self.status, 'secondary')


class PatientVisit(models.Model):
    """Tracks patient clinic visits per doctor per local day."""

    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="clinic_visits")
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name="patient_visits")
    visit_date = models.DateField()
    first_seen_at = models.DateTimeField()
    last_seen_at = models.DateTimeField()
    check_in_count = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Patient Visit"
        verbose_name_plural = "Patient Visits"
        ordering = ["-visit_date", "-last_seen_at"]
        unique_together = ("patient", "doctor", "visit_date")

    def __str__(self):
        return f"{self.visit_date} | {self.patient.username} -> Dr. {self.doctor.user.username}"
