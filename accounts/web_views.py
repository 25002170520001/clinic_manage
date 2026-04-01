from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import csv

from accounts.models import PatientProfile
from appointments.models import Appointment
from billing.models import Bill, ClinicSettings, Prescription
from doctors.models import Doctor
from token_queue.models import PatientVisit, QueueToken
from token_queue.time_utils import filter_today

from .device import is_mobile_request
from .forms import (
    DoctorCreateForm,
    DoctorUpdateForm,
    PatientCreateForm,
    PatientQuickProfileForm,
    PatientSignupForm,
    PatientQuickUserForm,
    ReceptionistCreateForm,
    StaffUserUpdateForm,
    StyledAuthenticationForm,
    UserProfileForm,
)


def home_page(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    top_doctor = (
        Doctor.objects.select_related("user")
        .filter(is_available=True)
        .order_by("-experience", "user__first_name", "user__username")
        .first()
    )
    doctor_count = Doctor.objects.count()
    available_count = Doctor.objects.filter(is_available=True).count()
    specialization_counts = (
        Doctor.objects.values("specialization").annotate(total=Count("id")).order_by("-total", "specialization")[:8]
    )
    context = {
        "top_doctor": top_doctor,
        "doctor_count": doctor_count,
        "available_doctor_count": available_count,
        "specialization_counts": specialization_counts,
    }
    template = "mobile/home.html" if is_mobile_request(request) else "home.html"
    return render(request, template, context)


def offline_view(request):
    return render(request, "offline.html")


class WebLoginView(LoginView):
    template_name = "auth/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return "/dashboard/"


@require_http_methods(["GET", "POST"])
def patient_signup_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = PatientSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.role = "patient"
        user.set_password(form.cleaned_data["password"])
        user.save()
        PatientProfile.objects.get_or_create(user=user)
        login(request, user)
        messages.success(request, "Account created successfully.")
        return redirect("dashboard")

    return render(request, "auth/signup.html", {"form": form})


@login_required
def dashboard_view(request):
    if request.user.is_superuser or request.user.role == "admin":
        return redirect("dashboard-admin")
    if request.user.role == "doctor":
        return redirect("dashboard-doctor")
    if request.user.role == "receptionist":
        return redirect("dashboard-receptionist")
    return redirect("dashboard-patient")


@login_required
def admin_dashboard_view(request):
    if not _is_admin_user(request.user):
        messages.error(request, "You do not have access to the admin dashboard.")
        return redirect("dashboard")

    today = timezone.localdate()
    available_doctors = Doctor.objects.filter(is_available=True).count()
    missed_today = filter_today(QueueToken.objects.filter(status="missed")).count()
    admin_notifications = []
    if available_doctors <= 1:
        admin_notifications.append(
            {
                "level": "warning",
                "text": f"Low doctor availability: only {available_doctors} doctor(s) marked available.",
            }
        )
    if missed_today > 0:
        admin_notifications.append(
            {
                "level": "warning",
                "text": f"{missed_today} token(s) marked missed today. Review queue handling.",
            }
        )
    if not admin_notifications:
        admin_notifications.append({"level": "info", "text": "All operational indicators look stable."})

    context = {
        "doctor_count": Doctor.objects.count(),
        "receptionist_count": request.user.__class__.objects.filter(role="receptionist").count(),
        "patient_count": request.user.__class__.objects.filter(role="patient").count(),
        "today_appointments": filter_today(Appointment.objects.all(), field_name="booking_time").count(),
        "waiting_tokens": filter_today(QueueToken.objects.filter(status="waiting")).count(),
        "called_tokens": filter_today(QueueToken.objects.filter(status="called")).count(),
        "in_consultation_tokens": filter_today(QueueToken.objects.filter(status="in_consultation")).count(),
        "today_clinic_patients": filter_today(PatientVisit.objects.all(), field_name="first_seen_at")
        .values("patient")
        .distinct()
        .count(),
        "total_clinic_patient_visits": PatientVisit.objects.count(),
        "total_unique_clinic_patients": PatientVisit.objects.values("patient").distinct().count(),
        "tokens_issued_today": filter_today(QueueToken.objects.all()).count(),
        "latest_token_today": filter_today(QueueToken.objects.all()).order_by("-token_number", "-created_at").first(),
        "recent_appointments": Appointment.objects.select_related("patient", "doctor__user").order_by("-created_at")[:6],
        "doctor_queue_snapshot": Doctor.objects.select_related("user")
        .annotate(
            waiting_count=Count(
                "queue_tokens",
                filter=Q(queue_tokens__created_at__date=today, queue_tokens__status="waiting"),
            )
        )
        .order_by("-waiting_count", "user__first_name")[:6],
        "doctor_availability": Doctor.objects.select_related("user").order_by("user__first_name", "user__username"),
        "admin_notifications": admin_notifications,
        "pending_bills_count": Bill.objects.filter(status="pending").count(),
        "paid_bills_count": Bill.objects.filter(status="paid").count(),
        "clinic_payment_settings": ClinicSettings.get_solo(),
    }
    return render(request, "dashboard/admin.html", context)


@login_required
def doctor_dashboard_view(request):
    if request.user.role != "doctor":
        messages.error(request, "You do not have access to the doctor dashboard.")
        return redirect("dashboard")

    doctor = Doctor.objects.filter(user=request.user).first()
    if not doctor:
        messages.error(request, "Doctor profile not found.")
        return redirect("home")

    today = timezone.localdate()
    waiting_queryset = filter_today(QueueToken.objects.filter(doctor=doctor, status="waiting")).order_by(
        "-priority", "token_number"
    )
    context = {
        "doctor": doctor,
        "today_appointments": filter_today(Appointment.objects.filter(doctor=doctor), field_name="booking_time").count(),
        "queue_waiting": waiting_queryset.count(),
        "in_consultation": filter_today(
            QueueToken.objects.filter(doctor=doctor, status="in_consultation")
        ).count(),
        "completed_today": filter_today(QueueToken.objects.filter(doctor=doctor, status="completed")).count(),
        "next_token": waiting_queryset.first(),
        "recent_completed_tokens": filter_today(
            QueueToken.objects.filter(doctor=doctor, status="completed")
        ).select_related("patient")[:6],
        "today_doctor_patients": filter_today(
            PatientVisit.objects.filter(doctor=doctor), field_name="first_seen_at"
        )
        .values("patient")
        .distinct()
        .count(),
        "total_doctor_patient_visits": PatientVisit.objects.filter(doctor=doctor).count(),
        "total_doctor_unique_patients": PatientVisit.objects.filter(doctor=doctor).values("patient").distinct().count(),
        "tokens_issued_today_doctor": filter_today(QueueToken.objects.filter(doctor=doctor)).count(),
        "latest_token_today_doctor": filter_today(QueueToken.objects.filter(doctor=doctor)).order_by(
            "-token_number", "-created_at"
        ).first(),
        "current_active_token": filter_today(
            QueueToken.objects.filter(doctor=doctor, status__in=["called", "in_consultation"])
        ).order_by("-priority", "token_number").first(),
        "doctor_is_available": doctor.is_available,
    }
    current_token = context["current_active_token"]
    if current_token:
        profile, _ = PatientProfile.objects.get_or_create(user=current_token.patient)
        context["current_patient_profile"] = profile
        context["current_patient_recent_prescriptions"] = Prescription.objects.filter(
            patient=current_token.patient, doctor=doctor
        ).order_by("-created_at")[:5]
        context["current_patient_recent_visits"] = PatientVisit.objects.filter(
            patient=current_token.patient, doctor=doctor
        ).order_by("-visit_date")[:5]
        context["current_patient_last_prescription"] = Prescription.objects.filter(
            patient=current_token.patient
        ).select_related("doctor__user").order_by("-created_at").first()
        context["current_patient_today_visit"] = filter_today(
            PatientVisit.objects.filter(patient=current_token.patient, doctor=doctor), field_name="first_seen_at"
        ).order_by("-last_seen_at").first()
        context["current_patient_today_tokens"] = filter_today(
            QueueToken.objects.filter(patient=current_token.patient, doctor=doctor)
        ).order_by("-created_at")
        context["current_patient_total_appointments"] = Appointment.objects.filter(patient=current_token.patient).count()
        context["current_patient_completed_appointments"] = Appointment.objects.filter(
            patient=current_token.patient, status="completed"
        ).count()
        context["current_patient_cancelled_appointments"] = Appointment.objects.filter(
            patient=current_token.patient, status="cancelled"
        ).count()
    return render(request, "dashboard/doctor.html", context)


@login_required
def receptionist_dashboard_view(request):
    if request.user.role != "receptionist":
        messages.error(request, "You do not have access to the receptionist dashboard.")
        return redirect("dashboard")

    available_doctors = Doctor.objects.filter(is_available=True).count()
    missed_today = filter_today(QueueToken.objects.filter(status="missed")).count()
    reception_alerts = []
    if available_doctors <= 1:
        reception_alerts.append(f"Only {available_doctors} doctor(s) available. Inform admin if needed.")
    if missed_today > 0:
        reception_alerts.append(f"{missed_today} missed token(s) today. Track patient announcements carefully.")

    today = timezone.localdate()
    context = {
        "today_appointments": filter_today(Appointment.objects.all(), field_name="booking_time").count(),
        "walkins_today": filter_today(QueueToken.objects.filter(is_walk_in=True)).count(),
        "waiting_tokens": filter_today(QueueToken.objects.filter(status="waiting")).count(),
        "called_tokens": filter_today(QueueToken.objects.filter(status="called")).count(),
        "recent_tokens": filter_today(QueueToken.objects.all())
        .select_related("patient", "doctor__user")
        .order_by("-created_at")[:8],
        "doctor_load": Doctor.objects.select_related("user")
        .annotate(
            waiting_count=Count(
                "queue_tokens",
                filter=Q(queue_tokens__created_at__date=today, queue_tokens__status="waiting"),
            )
        )
        .order_by("-waiting_count", "user__first_name")[:8],
        "tokens_issued_today": filter_today(QueueToken.objects.all()).count(),
        "latest_token_today": filter_today(QueueToken.objects.all()).order_by("-token_number", "-created_at").first(),
        "reception_alerts": reception_alerts,
    }
    return render(request, "dashboard/receptionist.html", context)


@login_required
def patient_dashboard_view(request):
    active_token = QueueToken.objects.filter(
        patient=request.user, status__in=["waiting", "called", "in_consultation"]
    ).order_by("-created_at").first()
    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    user_fields = ["first_name", "last_name", "email", "phone", "date_of_birth", "address"]
    profile_fields = ["blood_group", "emergency_contact", "allergies", "medical_history"]
    total_fields = len(user_fields) + len(profile_fields)
    filled_fields = sum(1 for f in user_fields if getattr(request.user, f)) + sum(
        1 for f in profile_fields if getattr(profile, f)
    )
    completion_percent = int((filled_fields / total_fields) * 100) if total_fields else 0

    context = {
        "my_total_appointments": Appointment.objects.filter(patient=request.user).count(),
        "my_today_appointments": filter_today(
            Appointment.objects.filter(patient=request.user), field_name="booking_time"
        ).count(),
        "my_upcoming": Appointment.objects.filter(
            patient=request.user, status__in=["pending", "confirmed"]
        ).count(),
        "active_token": active_token,
        "recent_appointments": Appointment.objects.filter(patient=request.user)
        .select_related("doctor__user")
        .order_by("-created_at")[:6],
        "profile_completion_percent": completion_percent,
        "quick_user_form": PatientQuickUserForm(instance=request.user),
        "quick_profile_form": PatientQuickProfileForm(instance=profile),
    }
    template = "mobile/dashboard_patient.html" if is_mobile_request(request) else "dashboard/patient.html"
    return render(request, template, context)


@login_required
def theme_settings_view(request):
    return render(request, "settings/theme.html")


@login_required
@require_http_methods(["GET", "POST"])
def profile_view(request):
    is_patient = request.user.role == "patient"
    patient_profile = None
    if is_patient:
        patient_profile, _ = PatientProfile.objects.get_or_create(user=request.user)

    user_form = UserProfileForm(request.POST or None, instance=request.user)
    patient_form = PatientQuickProfileForm(request.POST or None, instance=patient_profile) if is_patient else None

    if request.method == "POST":
        user_valid = user_form.is_valid()
        patient_valid = patient_form.is_valid() if patient_form else True
        if user_valid and patient_valid:
            user_form.save()
            if patient_form:
                patient_form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
        messages.error(request, "Please fix highlighted fields.")

    display_name = request.user.get_full_name().strip() or request.user.username
    context = {
        "user_form": user_form,
        "patient_form": patient_form,
        "display_name": display_name,
        "avatar_initial": display_name[0].upper(),
    }
    return render(request, "settings/profile.html", context)


@login_required
@require_http_methods(["POST"])
def patient_profile_quick_update_view(request):
    if request.user.role != "patient":
        messages.error(request, "Only patients can update profile from this page.")
        return redirect("dashboard")

    profile, _ = PatientProfile.objects.get_or_create(user=request.user)
    user_form = PatientQuickUserForm(request.POST, instance=request.user)
    profile_form = PatientQuickProfileForm(request.POST, instance=profile)
    if user_form.is_valid() and profile_form.is_valid():
        user_form.save()
        profile_form.save()
        messages.success(request, "Profile updated successfully.")
    else:
        messages.error(request, "Please correct the highlighted profile fields.")
    return redirect("dashboard-patient")


@login_required
@require_http_methods(["POST"])
def web_logout_view(request):
    logout(request)
    messages.info(request, "Logged out.")
    return redirect("home")


def _is_admin_user(user):
    return user.is_authenticated and (user.is_superuser or user.role == "admin")


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["POST"])
def admin_toggle_doctor_availability_view(request, doctor_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    doctor.is_available = not doctor.is_available
    doctor.save(update_fields=["is_available", "updated_at"])
    messages.success(
        request,
        f"Dr. {doctor.user.get_full_name() or doctor.user.username} is now "
        f"{'Available' if doctor.is_available else 'Unavailable'}.",
    )
    return redirect(request.POST.get("next") or "dashboard-admin")


@login_required
@require_http_methods(["POST"])
def doctor_toggle_availability_view(request):
    if request.user.role != "doctor":
        messages.error(request, "Only doctors can change this setting.")
        return redirect("dashboard")

    doctor = get_object_or_404(Doctor, user=request.user)
    doctor.is_available = not doctor.is_available
    doctor.save(update_fields=["is_available", "updated_at"])
    messages.success(
        request,
        f"Your status is now {'Available' if doctor.is_available else 'Unavailable'} for online booking and walk-ins.",
    )
    return redirect(request.POST.get("next") or "dashboard-doctor")


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["GET", "POST"])
def admin_staff_management_view(request):
    receptionist_form = ReceptionistCreateForm(prefix="rec")
    doctor_form = DoctorCreateForm(prefix="doc")
    patient_form = PatientCreateForm(prefix="pat")

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "receptionist":
            receptionist_form = ReceptionistCreateForm(request.POST, prefix="rec")
            if receptionist_form.is_valid():
                receptionist = receptionist_form.save(commit=False)
                receptionist.role = "receptionist"
                receptionist.set_password(receptionist_form.cleaned_data["password"])
                receptionist.save()
                messages.success(request, "Receptionist account created.")
                return redirect("admin-staff-management")

        elif form_type == "doctor":
            doctor_form = DoctorCreateForm(request.POST, prefix="doc")
            if doctor_form.is_valid():
                user_model = request.user.__class__
                doctor_user = user_model.objects.create_user(
                    username=doctor_form.cleaned_data["username"],
                    email=doctor_form.cleaned_data["email"],
                    password=doctor_form.cleaned_data["password"],
                    role="doctor",
                    first_name=doctor_form.cleaned_data["first_name"],
                    last_name=doctor_form.cleaned_data["last_name"],
                    phone=doctor_form.cleaned_data["phone"],
                )

                doctor = doctor_form.save(commit=False)
                doctor.user = doctor_user
                doctor.save()
                messages.success(request, "Doctor account created.")
                return redirect("admin-staff-management")
        elif form_type == "patient":
            patient_form = PatientCreateForm(request.POST, prefix="pat")
            if patient_form.is_valid():
                patient = patient_form.save(commit=False)
                patient.role = "patient"
                patient.set_password(patient_form.cleaned_data["password"])
                patient.save()
                PatientProfile.objects.get_or_create(user=patient)
                messages.success(request, "Patient account created.")
                return redirect("admin-staff-management")

    query = (request.GET.get("q") or "").strip()
    role_filter = request.GET.get("role", "all")
    active_filter = request.GET.get("active", "all")

    receptionists = request.user.__class__.objects.filter(role="receptionist")
    patients = request.user.__class__.objects.filter(role="patient")
    doctors = Doctor.objects.select_related("user").all()
    all_doctors = Doctor.objects.select_related("user").order_by("user__username")

    if query:
        receptionists = receptionists.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
        patients = patients.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
        doctors = doctors.filter(
            Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(user__email__icontains=query)
            | Q(user__phone__icontains=query)
            | Q(specialization__icontains=query)
            | Q(qualification__icontains=query)
        )

    if active_filter in {"active", "inactive"}:
        is_active = active_filter == "active"
        receptionists = receptionists.filter(is_active=is_active)
        patients = patients.filter(is_active=is_active)
        doctors = doctors.filter(user__is_active=is_active)

    show_receptionists = role_filter in {"all", "receptionist"}
    show_doctors = role_filter in {"all", "doctor"}
    show_patients = role_filter in {"all", "patient"}

    receptionists = receptionists.order_by("username")
    patients = patients.order_by("username")
    doctors = doctors.order_by("user__username")

    return render(
        request,
        "admin/staff_management.html",
        {
            "receptionist_form": receptionist_form,
            "doctor_form": doctor_form,
            "patient_form": patient_form,
            "receptionists": receptionists,
            "patients": patients,
            "doctors": doctors,
            "all_doctors": all_doctors,
            "query": query,
            "role_filter": role_filter,
            "active_filter": active_filter,
            "show_receptionists": show_receptionists,
            "show_doctors": show_doctors,
            "show_patients": show_patients,
        },
    )


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["GET"])
def admin_staff_export_view(request, role):
    role = role.lower().strip()
    if role not in {"doctor", "receptionist", "patient"}:
        return HttpResponse("Invalid role", status=400)

    query = (request.GET.get("q") or "").strip()
    active_filter = request.GET.get("active", "all")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{role}_export.csv"'
    writer = csv.writer(response)

    if role == "doctor":
        qs = Doctor.objects.select_related("user").all()
        if query:
            qs = qs.filter(
                Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(user__phone__icontains=query)
                | Q(specialization__icontains=query)
                | Q(qualification__icontains=query)
            )
        if active_filter in {"active", "inactive"}:
            qs = qs.filter(user__is_active=(active_filter == "active"))
        qs = qs.order_by("user__username")

        writer.writerow(["username", "full_name", "email", "phone", "specialization", "is_available", "is_active"])
        for d in qs:
            writer.writerow(
                [
                    d.user.username,
                    d.user.get_full_name(),
                    d.user.email or "",
                    d.user.phone or "",
                    d.specialization or "",
                    "yes" if d.is_available else "no",
                    "yes" if d.user.is_active else "no",
                ]
            )
    else:
        user_model = get_user_model()
        qs = user_model.objects.filter(role=role)
        if query:
            qs = qs.filter(
                Q(username__icontains=query)
                | Q(first_name__icontains=query)
                | Q(last_name__icontains=query)
                | Q(email__icontains=query)
                | Q(phone__icontains=query)
            )
        if active_filter in {"active", "inactive"}:
            qs = qs.filter(is_active=(active_filter == "active"))
        qs = qs.order_by("username")

        writer.writerow(["username", "full_name", "email", "phone", "is_active"])
        for u in qs:
            writer.writerow([u.username, u.get_full_name(), u.email or "", u.phone or "", "yes" if u.is_active else "no"])

    return response


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["GET", "POST"])
def admin_user_edit_view(request, user_id):
    user_model = get_user_model()
    target = get_object_or_404(user_model, id=user_id, role__in=["receptionist", "patient"])
    form = StaffUserUpdateForm(request.POST or None, instance=target)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        new_password = form.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
            user.save(update_fields=["password"])
        messages.success(request, f"{target.role.title()} updated.")
        return redirect("admin-staff-management")

    return render(
        request,
        "admin/user_edit.html",
        {
            "target_user": target,
            "form": form,
        },
    )


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["POST"])
def admin_user_delete_view(request, user_id):
    user_model = get_user_model()
    target = get_object_or_404(user_model, id=user_id, role__in=["receptionist", "patient"])
    role_label = target.role.title()
    username = target.username
    target.delete()
    messages.success(request, f"{role_label} '{username}' deleted.")
    return redirect("admin-staff-management")


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["GET", "POST"])
def admin_doctor_edit_view(request, doctor_id):
    doctor = get_object_or_404(Doctor.objects.select_related("user"), id=doctor_id)
    form = DoctorUpdateForm(request.POST or None, instance=doctor)

    if request.method == "POST" and form.is_valid():
        updated_doctor = form.save()
        user = updated_doctor.user
        user.username = form.cleaned_data["username"]
        user.email = form.cleaned_data.get("email", "")
        user.first_name = form.cleaned_data.get("first_name", "")
        user.last_name = form.cleaned_data.get("last_name", "")
        user.phone = form.cleaned_data.get("phone", "")
        new_password = form.cleaned_data.get("new_password")
        if new_password:
            user.set_password(new_password)
        user.save()
        messages.success(request, f"Doctor '{user.username}' updated.")
        return redirect("admin-staff-management")

    return render(
        request,
        "admin/doctor_edit.html",
        {
            "doctor": doctor,
            "form": form,
        },
    )


@login_required
@user_passes_test(_is_admin_user)
@require_http_methods(["POST"])
def admin_doctor_delete_view(request, doctor_id):
    doctor = get_object_or_404(Doctor.objects.select_related("user"), id=doctor_id)
    username = doctor.user.username
    doctor.user.delete()
    messages.success(request, f"Doctor '{username}' deleted.")
    return redirect("admin-staff-management")
