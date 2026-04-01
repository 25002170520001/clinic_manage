from django.urls import path

from .web_views import CancelAppointmentView, PatientAppointmentListView, PatientBookAppointmentView

urlpatterns = [
    path("patient/appointments/book/", PatientBookAppointmentView.as_view(), name="patient-book-appointment"),
    path("patient/appointments/my/", PatientAppointmentListView.as_view(), name="patient-appointments"),
    path("patient/appointments/<int:pk>/cancel/", CancelAppointmentView.as_view(), name="patient-cancel-appointment"),
]
