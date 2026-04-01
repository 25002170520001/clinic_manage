from django.contrib import admin

from .models import Bill, ClinicSettings, NotificationDelivery, Payment, Prescription, PrescriptionMedicine


@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ("bill_number", "patient", "doctor", "total_amount", "status", "email_sent", "created_at")
    list_filter = ("status", "email_sent", "created_at")
    search_fields = ("bill_number", "patient__username", "patient__first_name", "doctor__user__first_name")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "bill", "amount", "payment_method", "transaction_id", "created_at")
    list_filter = ("payment_method", "created_at")
    search_fields = ("bill__bill_number", "transaction_id")


@admin.register(ClinicSettings)
class ClinicSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "cash_enabled", "online_enabled", "sms_enabled", "whatsapp_enabled", "upi_id", "updated_at")


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "patient", "doctor", "appointment", "created_at", "email_sent")
    list_filter = ("email_sent", "created_at")
    search_fields = ("patient__username", "doctor__user__username")


@admin.register(PrescriptionMedicine)
class PrescriptionMedicineAdmin(admin.ModelAdmin):
    list_display = ("id", "prescription", "medicine_name", "times_per_day", "duration_days", "timing")
    list_filter = ("timing",)
    search_fields = ("medicine_name",)


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display = ("id", "channel", "status", "recipient", "bill", "prescription", "created_at")
    list_filter = ("channel", "status", "created_at")
    search_fields = ("recipient", "subject", "external_id", "bill__bill_number")
