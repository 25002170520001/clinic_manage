import json
import os
import urllib.error
import urllib.request

from django.core import signing
from django.urls import reverse

from billing.models import NotificationDelivery


class NotificationService:
    BILL_SALT = "billing.bill.share"
    PRESCRIPTION_SALT = "billing.prescription.share"

    @staticmethod
    def generate_share_token(kind, obj_id, patient_id):
        salt = NotificationService.BILL_SALT if kind == "bill" else NotificationService.PRESCRIPTION_SALT
        return signing.dumps(
            {
                "kind": kind,
                "id": obj_id,
                "patient_id": patient_id,
            },
            salt=salt,
        )

    @staticmethod
    def verify_share_token(token):
        max_age_seconds = int(os.getenv("DOCUMENT_LINK_EXPIRY_SECONDS", "86400"))
        last_error = None
        for salt in [NotificationService.BILL_SALT, NotificationService.PRESCRIPTION_SALT]:
            try:
                return signing.loads(token, salt=salt, max_age=max_age_seconds)
            except signing.BadSignature as exc:
                last_error = exc
        raise signing.BadSignature(str(last_error or "Invalid token"))

    @staticmethod
    def _build_absolute_url(request, path):
        if request is not None:
            return request.build_absolute_uri(path)
        base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
        if base_url:
            return f"{base_url}{path}"
        return path

    @staticmethod
    def build_bill_link(request, bill):
        token = NotificationService.generate_share_token("bill", bill.id, bill.patient_id)
        return NotificationService._build_absolute_url(request, reverse("bill-share-download", kwargs={"token": token}))

    @staticmethod
    def build_prescription_link(request, prescription):
        token = NotificationService.generate_share_token("prescription", prescription.id, prescription.patient_id)
        return NotificationService._build_absolute_url(
            request,
            reverse("prescription-share-download", kwargs={"token": token}),
        )

    @staticmethod
    def _post_json(url, payload, headers=None):
        encoded = json.dumps(payload).encode("utf-8")
        req_headers = {"Content-Type": "application/json"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, data=encoded, headers=req_headers, method="POST")
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read().decode("utf-8", errors="ignore")
            status = response.getcode()
        return status, body

    @staticmethod
    def _log(channel, status, recipient, bill=None, prescription=None, subject=None, message=None, error=None):
        NotificationDelivery.objects.create(
            channel=channel,
            status=status,
            recipient=recipient or "",
            subject=subject,
            message=message,
            error=error,
            bill=bill,
            prescription=prescription,
        )

    @staticmethod
    def send_sms(phone, message, bill=None, prescription=None):
        if not phone:
            NotificationService._log("sms", "skipped", "", bill=bill, prescription=prescription, message=message, error="Missing phone")
            return False, "Missing phone"

        sms_api_url = os.getenv("SMS_API_URL", "").strip()
        sms_api_key = os.getenv("SMS_API_KEY", "").strip()
        if not sms_api_url:
            NotificationService._log(
                "sms",
                "skipped",
                phone,
                bill=bill,
                prescription=prescription,
                message=message,
                error="SMS_API_URL not configured",
            )
            return False, "SMS provider not configured"

        payload = {"to": phone, "message": message}
        headers = {"Authorization": f"Bearer {sms_api_key}"} if sms_api_key else {}
        try:
            status, _ = NotificationService._post_json(sms_api_url, payload, headers=headers)
            if 200 <= status < 300:
                NotificationService._log("sms", "sent", phone, bill=bill, prescription=prescription, message=message)
                return True, ""
            NotificationService._log(
                "sms",
                "failed",
                phone,
                bill=bill,
                prescription=prescription,
                message=message,
                error=f"HTTP {status}",
            )
            return False, f"HTTP {status}"
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            NotificationService._log(
                "sms",
                "failed",
                phone,
                bill=bill,
                prescription=prescription,
                message=message,
                error=str(exc),
            )
            return False, str(exc)

    @staticmethod
    def send_whatsapp(phone, message, media_urls=None, bill=None, prescription=None):
        if not phone:
            NotificationService._log(
                "whatsapp",
                "skipped",
                "",
                bill=bill,
                prescription=prescription,
                message=message,
                error="Missing phone",
            )
            return False, "Missing phone"

        whatsapp_api_url = os.getenv("WHATSAPP_API_URL", "").strip()
        whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "").strip()
        if not whatsapp_api_url:
            NotificationService._log(
                "whatsapp",
                "skipped",
                phone,
                bill=bill,
                prescription=prescription,
                message=message,
                error="WHATSAPP_API_URL not configured",
            )
            return False, "WhatsApp provider not configured"

        payload = {
            "to": phone,
            "message": message,
            # Many providers can send documents via media URL; keep it optional.
            "media_urls": media_urls or [],
        }
        headers = {"Authorization": f"Bearer {whatsapp_api_key}"} if whatsapp_api_key else {}
        try:
            status, _ = NotificationService._post_json(whatsapp_api_url, payload, headers=headers)
            if 200 <= status < 300:
                NotificationService._log("whatsapp", "sent", phone, bill=bill, prescription=prescription, message=message)
                return True, ""
            NotificationService._log(
                "whatsapp",
                "failed",
                phone,
                bill=bill,
                prescription=prescription,
                message=message,
                error=f"HTTP {status}",
            )
            return False, f"HTTP {status}"
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            NotificationService._log(
                "whatsapp",
                "failed",
                phone,
                bill=bill,
                prescription=prescription,
                message=message,
                error=str(exc),
            )
            return False, str(exc)

    @staticmethod
    def notify_payment_documents(request, bill, prescription=None, send_sms_enabled=True, send_whatsapp_enabled=True):
        bill_link = NotificationService.build_bill_link(request, bill)
        prescription_link = NotificationService.build_prescription_link(request, prescription) if prescription else ""
        links_text = f"Bill: {bill_link}"
        if prescription_link:
            links_text += f" | Prescription: {prescription_link}"
        sms_message = (
            f"Family Health Care: Payment received for {bill.bill_number}. "
            f"Amount INR {bill.total_amount}. {links_text}"
        )
        whatsapp_message = (
            f"Family Health Care\n"
            f"Payment Received: {bill.bill_number}\n"
            f"Amount: INR {bill.total_amount}\n"
            f"{links_text}"
        )
        if send_sms_enabled:
            sms_ok, sms_error = NotificationService.send_sms(
                phone=bill.patient.phone,
                message=sms_message,
                bill=bill,
                prescription=prescription,
            )
        else:
            sms_ok, sms_error = False, "Disabled by admin"
            NotificationService._log(
                "sms",
                "skipped",
                bill.patient.phone or "",
                bill=bill,
                prescription=prescription,
                message=sms_message,
                error=sms_error,
            )

        if send_whatsapp_enabled:
            wa_ok, wa_error = NotificationService.send_whatsapp(
                phone=bill.patient.phone,
                message=whatsapp_message,
                media_urls=[u for u in [bill_link, prescription_link] if u],
                bill=bill,
                prescription=prescription,
            )
        else:
            wa_ok, wa_error = False, "Disabled by admin"
            NotificationService._log(
                "whatsapp",
                "skipped",
                bill.patient.phone or "",
                bill=bill,
                prescription=prescription,
                message=whatsapp_message,
                error=wa_error,
            )
        return {
            "sms_sent": sms_ok,
            "sms_error": sms_error,
            "whatsapp_sent": wa_ok,
            "whatsapp_error": wa_error,
            "bill_link": bill_link,
            "prescription_link": prescription_link,
        }
