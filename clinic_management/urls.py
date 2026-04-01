"""
URL configuration for clinic_management project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path

from clinic_management.pwa_views import manifest_view, service_worker_view

from accounts.web_views import (
    WebLoginView,
    admin_doctor_delete_view,
    admin_doctor_edit_view,
    admin_staff_management_view,
    admin_toggle_doctor_availability_view,
    admin_user_delete_view,
    admin_user_edit_view,
    admin_staff_export_view,
    admin_dashboard_view,
    dashboard_view,
    doctor_toggle_availability_view,
    doctor_dashboard_view,
    home_page,
    patient_dashboard_view,
    profile_view,
    patient_profile_quick_update_view,
    patient_signup_view,
    receptionist_dashboard_view,
    theme_settings_view,
    offline_view,
    web_logout_view,
)


urlpatterns = [
    path("", home_page, name="home"),
    path("manifest.webmanifest", manifest_view, name="pwa-manifest"),
    path("sw.js", service_worker_view, name="pwa-sw"),
    path("offline/", offline_view, name="offline-page"),
    path("login/", WebLoginView.as_view(), name="web-login"),
    path("signup/", patient_signup_view, name="patient-signup"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("dashboard/admin/", admin_dashboard_view, name="dashboard-admin"),
    path("dashboard/doctor/", doctor_dashboard_view, name="dashboard-doctor"),
    path("dashboard/receptionist/", receptionist_dashboard_view, name="dashboard-receptionist"),
    path("dashboard/patient/", patient_dashboard_view, name="dashboard-patient"),
    path("profile/", profile_view, name="profile"),
    path("dashboard/patient/profile/update/", patient_profile_quick_update_view, name="patient-profile-quick-update"),
    path("settings/theme/", theme_settings_view, name="theme-settings"),
    path("dashboard/doctor/availability/toggle/", doctor_toggle_availability_view, name="doctor-toggle-availability"),
    path("logout/", web_logout_view, name="web-logout"),
    path("admin/staff/", admin_staff_management_view, name="admin-staff-management"),
    path(
        "admin/doctors/<int:doctor_id>/availability/toggle/",
        admin_toggle_doctor_availability_view,
        name="admin-toggle-doctor-availability",
    ),
    path("admin/staff/user/<int:user_id>/edit/", admin_user_edit_view, name="admin-user-edit"),
    path("admin/staff/user/<int:user_id>/delete/", admin_user_delete_view, name="admin-user-delete"),
    path("admin/staff/doctor/<int:doctor_id>/edit/", admin_doctor_edit_view, name="admin-doctor-edit"),
    path("admin/staff/doctor/<int:doctor_id>/delete/", admin_doctor_delete_view, name="admin-doctor-delete"),
    path("admin/staff/export/<str:role>/", admin_staff_export_view, name="admin-staff-export"),
    path("", include("appointments.web_urls")),
    path("", include("billing.web_urls")),
    path("", include("token_queue.web_urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("doctors/", include("doctors.urls")),
    path("appointments/", include("appointments.urls")),
    path("queue/", include("token_queue.urls")),
]
