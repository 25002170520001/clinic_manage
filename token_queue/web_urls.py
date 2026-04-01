from django.urls import path

from .web_views import (
    AddPrescriptionView,
    DoctorCallNextView,
    DoctorQueueView,
    DoctorTokenActionView,
    QueueDisplayDataView,
    QueueDisplayView,
    ReceptionActionView,
    ReceptionCallNextView,
    ReceptionQueueView,
    TVLauncherView,
)

urlpatterns = [
    path("reception/", ReceptionQueueView.as_view(), name="web-reception-queue"),
    path("reception/tv/", TVLauncherView.as_view(), name="web-tv-launcher"),
    path("reception/token/<int:token_id>/<str:action>/", ReceptionActionView.as_view(), name="web-reception-token-action"),
    path("reception/doctor/<int:doctor_id>/call-next/", ReceptionCallNextView.as_view(), name="web-reception-call-next"),
    path("doctor/", DoctorQueueView.as_view(), name="web-doctor-queue"),
    path("doctor/call-next/", DoctorCallNextView.as_view(), name="web-doctor-call-next"),
    path("doctor/token/<int:token_id>/prescription/", AddPrescriptionView.as_view(), name="web-doctor-add-prescription"),
    path("doctor/token/<int:token_id>/<str:action>/", DoctorTokenActionView.as_view(), name="web-doctor-token-action"),
    path("display/<int:doctor_id>/", QueueDisplayView.as_view(), name="web-queue-display"),
    path("display/<int:doctor_id>/data/", QueueDisplayDataView.as_view(), name="web-queue-display-data"),
]
