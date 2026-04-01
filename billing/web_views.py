from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.core import signing
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View
from urllib.parse import quote

from accounts.decorators import role_required

from .forms import BillPaymentForm, ClinicSettingsForm
from .models import Bill, ClinicSettings, Payment, Prescription
from .services.billing_service import BillingService
from .services.notification_service import NotificationService
from .services.prescription_service import PrescriptionService


@method_decorator(role_required("patient"), name="dispatch")
class PatientPrescriptionListView(LoginRequiredMixin, TemplateView):
    template_name = "billing/patient_prescriptions.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["prescriptions"] = Prescription.objects.filter(patient=self.request.user).select_related(
            "doctor__user", "appointment"
        )
        return context


@method_decorator(role_required("patient", "doctor", "admin"), name="dispatch")
class PrescriptionPdfView(LoginRequiredMixin, View):
    def get(self, request, prescription_id):
        prescription = get_object_or_404(Prescription, id=prescription_id)

        if request.user.role == "patient" and prescription.patient != request.user:
            return HttpResponse("Forbidden", status=403)

        pdf_bytes = PrescriptionService.build_prescription_pdf(prescription)
        if not pdf_bytes:
            return render(
                request,
                "billing/prescription_print_fallback.html",
                {
                    "prescription": prescription,
                    "pdf_unavailable": True,
                    "auto_print": request.GET.get("autoprint") == "1",
                },
                status=200,
            )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="prescription_{prescription_id}.pdf"'
        return response


@method_decorator(role_required("patient", "doctor", "admin"), name="dispatch")
class PrescriptionPrintView(LoginRequiredMixin, View):
    def get(self, request, prescription_id):
        prescription = get_object_or_404(Prescription, id=prescription_id)

        if request.user.role == "patient" and prescription.patient != request.user:
            return HttpResponse("Forbidden", status=403)

        return render(
            request,
            "billing/prescription_print_fallback.html",
            {
                "prescription": prescription,
                "auto_print": True,
            },
            status=200,
        )


@method_decorator(role_required("patient", "receptionist", "doctor", "admin"), name="dispatch")
class BillPdfView(LoginRequiredMixin, View):
    def get(self, request, bill_id):
        bill = get_object_or_404(Bill.objects.select_related("patient"), id=bill_id)
        if request.user.role == "patient" and bill.patient != request.user:
            return HttpResponse("Forbidden", status=403)

        pdf_bytes = BillingService.build_bill_pdf(bill)
        if not pdf_bytes:
            return HttpResponse("Bill PDF generation failed.", status=500)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="{bill.bill_number}.pdf"'
        return response


class SharedDocumentDownloadView(View):
    def get(self, request, token):
        try:
            payload = NotificationService.verify_share_token(token)
        except signing.BadSignature:
            return HttpResponse("Link invalid or expired.", status=403)

        kind = payload.get("kind")
        obj_id = payload.get("id")
        patient_id = payload.get("patient_id")

        if kind == "bill":
            bill = get_object_or_404(Bill.objects.select_related("patient"), id=obj_id)
            if bill.patient_id != patient_id:
                return HttpResponse("Forbidden", status=403)
            pdf_bytes = BillingService.build_bill_pdf(bill)
            if not pdf_bytes:
                return HttpResponse("Bill PDF unavailable.", status=500)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{bill.bill_number}.pdf"'
            return response

        if kind == "prescription":
            prescription = get_object_or_404(Prescription.objects.select_related("patient"), id=obj_id)
            if prescription.patient_id != patient_id:
                return HttpResponse("Forbidden", status=403)
            pdf_bytes = PrescriptionService.build_prescription_pdf(prescription)
            if not pdf_bytes:
                return HttpResponse("Prescription PDF unavailable.", status=500)
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="prescription_{prescription.id}.pdf"'
            return response

        return HttpResponse("Invalid document link.", status=400)


@method_decorator(role_required("receptionist", "admin"), name="dispatch")
class BillingDeskView(LoginRequiredMixin, TemplateView):
    template_name = "billing/desk.html"

    @staticmethod
    def _clean_phone_for_whatsapp(phone):
        if not phone:
            return ""
        return "".join(ch for ch in str(phone) if ch.isdigit())

    def _build_manual_links(self, request, bill):
        patient_phone_raw = bill.patient.phone or ""
        patient_phone_wa = self._clean_phone_for_whatsapp(patient_phone_raw)
        prescription = BillingService._get_prescription_for_bill(bill)
        bill_link = NotificationService.build_bill_link(request, bill)
        prescription_link = NotificationService.build_prescription_link(request, prescription) if prescription else ""

        links_text = f"Bill: {bill_link}"
        if prescription_link:
            links_text += f" | Prescription: {prescription_link}"

        message = (
            f"Family Health Care: Payment received for {bill.bill_number}. "
            f"Amount INR {bill.total_amount}. {links_text}"
        )
        encoded = quote(message, safe="")

        sms_url = ""
        if patient_phone_raw:
            sms_url = f"sms:{patient_phone_raw}?body={encoded}"

        whatsapp_url = ""
        if patient_phone_wa:
            whatsapp_url = f"https://wa.me/{patient_phone_wa}?text={encoded}"

        return {
            "sms_url": sms_url,
            "whatsapp_url": whatsapp_url,
            "patient_phone": patient_phone_raw,
            "message": message,
            "bill_link": bill_link,
            "prescription_link": prescription_link,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_obj = ClinicSettings.get_solo()
        pending_bills = Bill.objects.filter(status="pending").select_related(
            "patient",
            "doctor__user",
            "appointment",
        ).order_by("created_at")[:30]
        recent_paid = Bill.objects.filter(status="paid").select_related(
            "patient",
            "doctor__user",
        ).order_by("-updated_at")[:30]
        recent_paid_rows = [{"bill": bill, "links": self._build_manual_links(self.request, bill)} for bill in recent_paid]
        context.update(
            {
                "clinic_settings": settings_obj,
                "settings_form": ClinicSettingsForm(instance=settings_obj),
                "pending_bills": pending_bills,
                "recent_paid_bills": recent_paid,
                "recent_paid_rows": recent_paid_rows,
            }
        )
        return context


@method_decorator(role_required("admin"), name="dispatch")
class ClinicSettingsUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        settings_obj = ClinicSettings.get_solo()
        form = ClinicSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Billing settings updated.")
            return redirect("web-billing-desk")
        messages.error(request, "Could not save billing settings. Check the fields below.")
        pending_bills = Bill.objects.filter(status="pending").select_related(
            "patient",
            "doctor__user",
            "appointment",
        ).order_by("created_at")[:30]
        recent_paid = Bill.objects.filter(status="paid").select_related(
            "patient",
            "doctor__user",
        ).order_by("-updated_at")[:30]
        return render(
            request,
            "billing/desk.html",
            {
                "clinic_settings": settings_obj,
                "settings_form": form,
                "pending_bills": pending_bills,
                "recent_paid_bills": recent_paid,
            },
            status=400,
        )


@method_decorator(role_required("receptionist", "admin"), name="dispatch")
class BillCollectPaymentView(LoginRequiredMixin, View):
    def post(self, request, bill_id):
        bill = get_object_or_404(Bill.objects.select_related("patient", "doctor__user"), id=bill_id)
        if bill.status == "paid":
            messages.info(request, f"{bill.bill_number} is already paid.")
            return redirect("web-billing-desk")

        settings_obj = ClinicSettings.get_solo()
        form = BillPaymentForm(request.POST, settings_obj=settings_obj)
        if form.is_valid():
            Payment.objects.create(
                bill=bill,
                amount=bill.total_amount,
                payment_method=form.cleaned_data["payment_method"],
                transaction_id=form.cleaned_data.get("transaction_id"),
                notes=form.cleaned_data.get("notes"),
            )
            bill.status = "paid"
            bill.save(update_fields=["status", "updated_at"])

            sent, error = BillingService.email_bill_and_prescription(bill)
            prescription = BillingService._get_prescription_for_bill(bill)
            notify_result = NotificationService.notify_payment_documents(
                request,
                bill,
                prescription=prescription,
                send_sms_enabled=settings_obj.sms_enabled,
                send_whatsapp_enabled=settings_obj.whatsapp_enabled,
            )
            if sent:
                messages.success(request, f"Payment collected for {bill.bill_number}. Bill and prescription emailed.")
            else:
                messages.warning(
                    request,
                    f"Payment collected for {bill.bill_number}, but email was not sent. {error}",
                )
            def _delivery_status(sent_flag, error_text):
                if sent_flag:
                    return "sent"
                normalized = (error_text or "").strip().lower()
                if (
                    "not configured" in normalized
                    or "missing phone" in normalized
                    or "disabled by admin" in normalized
                ):
                    return "skipped"
                return f"failed ({error_text})" if error_text else "failed"

            sms_status = _delivery_status(notify_result["sms_sent"], notify_result["sms_error"])
            wa_status = _delivery_status(notify_result["whatsapp_sent"], notify_result["whatsapp_error"])

            if sms_status == "sent" and wa_status == "sent":
                messages.success(request, "SMS + WhatsApp notification sent with secure document links.")
            elif sms_status == "skipped" and wa_status == "skipped":
                messages.info(
                    request,
                    "SMS/WhatsApp API skipped. Use the manual Send buttons in Recently Paid Bills to send from admin phone.",
                )
            else:
                messages.info(request, f"SMS: {sms_status} | WhatsApp: {wa_status}")
            return redirect("web-billing-desk")

        messages.error(request, "Payment could not be collected. Check method/transaction details.")

        pending_bills = Bill.objects.filter(status="pending").select_related(
            "patient",
            "doctor__user",
            "appointment",
        ).order_by("created_at")[:30]
        recent_paid = Bill.objects.filter(status="paid").select_related(
            "patient",
            "doctor__user",
        ).order_by("-updated_at")[:30]
        return render(
            request,
            "billing/desk.html",
            {
                "clinic_settings": settings_obj,
                "settings_form": ClinicSettingsForm(instance=settings_obj),
                "pending_bills": pending_bills,
                "recent_paid_bills": recent_paid,
            },
            status=400,
        )
