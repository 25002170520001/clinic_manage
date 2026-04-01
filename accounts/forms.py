from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm

from accounts.models import PatientProfile
from doctors.models import Doctor

User = get_user_model()


class StyledAuthenticationForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Username"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"}))


class PatientSignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"}))
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Confirm password"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "date_of_birth", "address"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"}),
            "first_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Last name"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "Phone"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "address": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Address"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data


class ReceptionistCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"}))

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "password"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"}),
            "first_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Last name"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "Phone"}),
        }


class DoctorCreateForm(forms.ModelForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Username"}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "First name"}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Last name"}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Phone"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"}))

    class Meta:
        model = Doctor
        fields = ["specialization", "qualification", "experience", "consultation_fee", "is_available"]
        widgets = {
            "specialization": forms.TextInput(attrs={"class": "form-input", "placeholder": "Specialization"}),
            "qualification": forms.TextInput(attrs={"class": "form-input", "placeholder": "Qualification"}),
            "experience": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
            "consultation_fee": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": 0}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }


class PatientCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Password"}))

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "password"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input", "placeholder": "Username"}),
            "email": forms.EmailInput(attrs={"class": "form-input", "placeholder": "Email"}),
            "first_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Last name"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "Phone"}),
        }


class StaffUserUpdateForm(forms.ModelForm):
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "New password (optional)"}),
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
        }

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Email already exists.")
        return email


class DoctorUpdateForm(forms.ModelForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "form-input"}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={"class": "form-input"}))
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    phone = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-input"}))
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "New password (optional)"}),
    )

    class Meta:
        model = Doctor
        fields = ["specialization", "qualification", "experience", "consultation_fee", "is_available"]
        widgets = {
            "specialization": forms.TextInput(attrs={"class": "form-input"}),
            "qualification": forms.TextInput(attrs={"class": "form-input"}),
            "experience": forms.NumberInput(attrs={"class": "form-input", "min": 0}),
            "consultation_fee": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": 0}),
            "is_available": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user = self.instance.user
            self.fields["username"].initial = user.username
            self.fields["email"].initial = user.email
            self.fields["first_name"].initial = user.first_name
            self.fields["last_name"].initial = user.last_name
            self.fields["phone"].initial = user.phone

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = User.objects.filter(username=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("Username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            return email
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.user_id)
        if qs.exists():
            raise forms.ValidationError("Email already exists.")
        return email


class PatientQuickUserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "date_of_birth", "address"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "address": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }


class PatientQuickProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = ["blood_group", "emergency_contact", "allergies", "medical_history"]
        widgets = {
            "blood_group": forms.TextInput(attrs={"class": "form-input"}),
            "emergency_contact": forms.TextInput(attrs={"class": "form-input"}),
            "allergies": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
            "medical_history": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "date_of_birth", "address"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "last_name": forms.TextInput(attrs={"class": "form-input"}),
            "email": forms.EmailInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "date_of_birth": forms.DateInput(attrs={"class": "form-input", "type": "date"}),
            "address": forms.Textarea(attrs={"class": "form-input", "rows": 2}),
        }
