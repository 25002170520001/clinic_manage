from django.urls import path

from .web_views import (
    BillingDeskView,
    BillPdfView,
    BillCollectPaymentView,
    ClinicSettingsUpdateView,
    PatientPrescriptionListView,
    PrescriptionPdfView,
    PrescriptionPrintView,
    SharedDocumentDownloadView,
)

urlpatterns = [
    path("patient/prescriptions/", PatientPrescriptionListView.as_view(), name="patient-prescriptions"),
    path("prescription/<int:prescription_id>/pdf/", PrescriptionPdfView.as_view(), name="prescription-pdf"),
    path("prescription/<int:prescription_id>/print/", PrescriptionPrintView.as_view(), name="prescription-print"),
    path("billing/bill/<int:bill_id>/pdf/", BillPdfView.as_view(), name="bill-pdf"),
    path("billing/desk/", BillingDeskView.as_view(), name="web-billing-desk"),
    path("billing/settings/update/", ClinicSettingsUpdateView.as_view(), name="web-billing-settings-update"),
    path("billing/bill/<int:bill_id>/collect/", BillCollectPaymentView.as_view(), name="web-bill-collect"),
    path("documents/share/<str:token>/", SharedDocumentDownloadView.as_view(), name="bill-share-download"),
    path("documents/share/rx/<str:token>/", SharedDocumentDownloadView.as_view(), name="prescription-share-download"),
]
