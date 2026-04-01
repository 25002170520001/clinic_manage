
from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'doctor', 'booking_time', 'status', 'created_at']
    list_filter = ['status', 'booking_time']
    search_fields = ['patient__username', 'patient__first_name', 'patient__last_name', 
                     'doctor__user__username', 'doctor__user__first_name']
    ordering = ['-booking_time']
    date_hierarchy = 'booking_time'

