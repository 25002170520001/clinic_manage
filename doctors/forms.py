from django import forms


class DoctorAvailabilityForm(forms.Form):
    is_available = forms.BooleanField(required=False)
