
from django.contrib import admin
from .models import PatientVisit, QueueToken


@admin.register(QueueToken)
class QueueTokenAdmin(admin.ModelAdmin):
    list_display = ['token_display', 'patient', 'doctor', 'priority', 'status', 'created_at']
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['patient__username', 'patient__first_name', 'doctor__user__username', 'token_display']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'


@admin.register(PatientVisit)
class PatientVisitAdmin(admin.ModelAdmin):
    list_display = ["visit_date", "patient", "doctor", "check_in_count", "first_seen_at", "last_seen_at"]
    list_filter = ["visit_date", "doctor"]
    search_fields = ["patient__username", "patient__first_name", "doctor__user__username"]
    ordering = ["-visit_date", "-last_seen_at"]
