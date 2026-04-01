from django import forms

from .models import ClinicSettings, Payment, Prescription


class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ["symptoms", "diagnosis", "dosage", "notes", "follow_up_date"]
        widgets = {
            "symptoms": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "diagnosis": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "dosage": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "follow_up_date": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
        }


class ClinicSettingsForm(forms.ModelForm):
    class Meta:
        model = ClinicSettings
        fields = [
            "cash_enabled",
            "online_enabled",
            "sms_enabled",
            "whatsapp_enabled",
            "upi_id",
            "upi_qr_image_url",
        ]
        widgets = {
            "upi_id": forms.TextInput(attrs={"class": "form-input", "placeholder": "example@upi"}),
            "upi_qr_image_url": forms.URLInput(attrs={"class": "form-input", "placeholder": "https://..."}),
        }

    def clean(self):
        cleaned = super().clean()
        cash_enabled = cleaned.get("cash_enabled")
        online_enabled = cleaned.get("online_enabled")
        if not cash_enabled and not online_enabled:
            raise forms.ValidationError("Enable at least one payment method (cash or online).")
        if online_enabled and not cleaned.get("upi_id"):
            self.add_error("upi_id", "UPI ID is required when online payment is enabled.")
        return cleaned


class BillPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ["payment_method", "transaction_id", "notes"]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-input"}),
            "transaction_id": forms.TextInput(attrs={"class": "form-input"}),
            "notes": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        settings = kwargs.pop("settings_obj", None)
        super().__init__(*args, **kwargs)
        self._settings = settings
        choices = []
        if not settings or settings.cash_enabled:
            choices.append(("cash", "Cash"))
        if settings and settings.online_enabled:
            choices.extend([("upi", "UPI"), ("online", "Online")])
        if not choices:
            choices = [("cash", "Cash")]
        self.fields["payment_method"].choices = choices

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get("payment_method")
        txn = (cleaned.get("transaction_id") or "").strip()
        settings = self._settings
        allowed = []
        if not settings or settings.cash_enabled:
            allowed.append("cash")
        if settings and settings.online_enabled:
            allowed.extend(["upi", "online"])
        if method and method not in allowed:
            raise forms.ValidationError("Selected payment method is disabled in clinic settings.")
        if method in {"upi", "online"} and not txn:
            self.add_error("transaction_id", "Transaction ID is required for online payment.")
        return cleaned
