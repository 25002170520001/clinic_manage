from django import forms
from django.contrib.auth import get_user_model

from doctors.models import Doctor

User = get_user_model()


class ReceptionTokenForm(forms.Form):
    existing_patient = forms.ModelChoiceField(
        queryset=User.objects.filter(role="patient").order_by("username"),
        required=False,
        widget=forms.Select(attrs={"class": "form-input"}),
        help_text="Select existing patient OR create a new one below.",
    )
    new_username = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    new_first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    new_last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    new_email = forms.EmailField(
        required=False,
        label="New email id",
        widget=forms.EmailInput(attrs={"class": "form-input"}),
    )
    new_phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.none(), widget=forms.Select(attrs={"class": "form-input"}))
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"class": "form-input", "rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["doctor"].queryset = Doctor.objects.filter(is_available=True).select_related("user")

    def clean(self):
        cleaned_data = super().clean()
        existing_patient = cleaned_data.get("existing_patient")
        new_username = (cleaned_data.get("new_username") or "").strip()
        if existing_patient and new_username:
            raise forms.ValidationError("Use existing patient OR new patient fields, not both.")
        if not existing_patient and not new_username:
            raise forms.ValidationError("Select existing patient or enter new patient username.")
        return cleaned_data


class CheckInForm(forms.Form):
    token = forms.IntegerField(widget=forms.HiddenInput())
