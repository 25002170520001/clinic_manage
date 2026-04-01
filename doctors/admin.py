
from django.contrib import admin
from .models import Doctor


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['user', 'specialization', 'qualification', 'experience', 'consultation_fee', 'is_available']
    list_filter = ['specialization', 'is_available']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'specialization']
    ordering = ['-created_at']

