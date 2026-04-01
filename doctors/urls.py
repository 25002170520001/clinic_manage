
from django.urls import path
from .views import (
    DoctorListCreateView,
    DoctorDetailView,
    AvailableDoctorsView,
    toggle_doctor_availability,
    get_doctor_by_user
)

urlpatterns = [
    path('', DoctorListCreateView.as_view(), name='doctor-list-create'),
    path('<int:pk>/', DoctorDetailView.as_view(), name='doctor-detail'),
    path('available/', AvailableDoctorsView.as_view(), name='available-doctors'),
    path('<int:pk>/toggle-availability/', toggle_doctor_availability, name='toggle-doctor-availability'),
    path('by-user/<int:user_id>/', get_doctor_by_user, name='doctor-by-user'),
]

