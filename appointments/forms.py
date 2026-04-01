from django import forms

from doctors.models import Doctor


class AppointmentBookingForm(forms.Form):
    doctor = forms.ModelChoiceField(queryset=Doctor.objects.none(), widget=forms.Select(attrs={"class": "form-input"}))
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Symptoms or notes"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        available_doctors = Doctor.objects.filter(is_available=True).select_related("user")
        self.fields["doctor"].queryset = available_doctors
        if available_doctors.exists():
            self.fields["doctor"].help_text = "Showing available doctors."
        else:
            self.fields["doctor"].help_text = "No doctor is available right now. Please contact reception."
