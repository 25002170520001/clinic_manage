
from django.db import models
from django.conf import settings
from doctors.models import Doctor
from appointments.models import Appointment


class Bill(models.Model):
    """Bill model for patient payments"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    bill_number = models.CharField(max_length=20, unique=True)
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bills')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='bills')
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='bills', blank=True, null=True)
    
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    medicine_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    other_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    email_sent = models.BooleanField(default=False)
    emailed_at = models.DateTimeField(blank=True, null=True)
    email_error = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'
        ordering = ['-created_at']

    def __str__(self):
        return f"Bill {self.bill_number} - {self.patient.username}"

    def calculate_total(self):
        """Calculate total amount"""
        return self.consultation_fee + self.medicine_cost + self.other_charges - self.discount


class Payment(models.Model):
    """Payment model for tracking transactions"""
    
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('upi', 'UPI'),
        ('online', 'Online'),
    ]

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.id} - {self.bill.bill_number}"


class ClinicSettings(models.Model):
    """Singleton-like clinic billing/payment settings."""

    cash_enabled = models.BooleanField(default=True)
    online_enabled = models.BooleanField(default=False)
    sms_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    upi_id = models.CharField(max_length=120, blank=True, null=True)
    upi_qr_image_url = models.URLField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clinic Settings"
        verbose_name_plural = "Clinic Settings"

    def __str__(self):
        return "Clinic Settings"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class Prescription(models.Model):
    """Prescription model for doctor consultations"""
    
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='prescriptions')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='prescriptions')
    
    symptoms = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    medicines = models.TextField()  # JSON or text format for medicines
    dosage = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    follow_up_date = models.DateField(blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    emailed_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Prescription {self.id} - {self.patient.username} - Dr. {self.doctor.user.username}"


class PrescriptionMedicine(models.Model):
    """Structured medicine rows for a prescription."""

    TIMING_CHOICES = [
        ("before_food", "Before Food"),
        ("after_food", "After Food"),
        ("with_food", "With Food"),
        ("bedtime", "Bedtime"),
        ("custom", "Custom"),
    ]

    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="medicine_items")
    medicine_name = models.CharField(max_length=200)
    dose = models.CharField(max_length=100, blank=True, null=True)
    times_per_day = models.PositiveIntegerField(default=1)
    duration_days = models.PositiveIntegerField(default=1)
    quantity_tablets = models.PositiveIntegerField(default=1)
    timing = models.CharField(max_length=20, choices=TIMING_CHOICES, default="after_food")
    instruction = models.CharField(max_length=200, blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "Prescription Medicine"
        verbose_name_plural = "Prescription Medicines"

    def __str__(self):
        return f"{self.medicine_name} ({self.prescription_id})"


class NotificationDelivery(models.Model):
    """Tracks outbound delivery attempts for patient communication."""

    CHANNEL_CHOICES = [
        ("email", "Email"),
        ("sms", "SMS"),
        ("whatsapp", "WhatsApp"),
    ]
    STATUS_CHOICES = [
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ]

    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="sent")
    recipient = models.CharField(max_length=160)
    subject = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    external_id = models.CharField(max_length=160, blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    bill = models.ForeignKey(Bill, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications")
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification Delivery"
        verbose_name_plural = "Notification Deliveries"

    def __str__(self):
        return f"{self.channel} -> {self.recipient} ({self.status})"
