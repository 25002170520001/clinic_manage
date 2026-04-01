
from django.urls import path
from .views import (
    AppointmentListCreateView,
    AppointmentDetailView,
    MyAppointmentsView,
    book_appointment,
    cancel_appointment,
    appointment_detail,
    today_appointments
)

urlpatterns = [
    path('', AppointmentListCreateView.as_view(), name='appointment-list-create'),
    path('<int:pk>/', AppointmentDetailView.as_view(), name='appointment-detail'),
    path('my/', MyAppointmentsView.as_view(), name='my-appointments'),
    path('book/', book_appointment, name='book-appointment'),
    path('<int:pk>/cancel/', cancel_appointment, name='cancel-appointment'),
    path('<int:pk>/detail/', appointment_detail, name='appointment-detail-api'),
    path('today/', today_appointments, name='today-appointments'),
]

