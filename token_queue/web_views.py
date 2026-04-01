from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.decorators import role_required
from accounts.models import PatientProfile
from appointments.models import Appointment
from billing.forms import PrescriptionForm
from billing.models import Prescription, PrescriptionMedicine
from billing.services.billing_service import BillingService
from billing.services.prescription_service import PrescriptionService
from doctors.models import Doctor

from .forms import ReceptionTokenForm
from .models import PatientVisit, QueueToken
from .services import QueueService
from .time_utils import filter_today

DEFAULT_PATIENT_PASSWORD = "Patient@123"


def _queue_for_doctor_today(doctor):
    return filter_today(QueueToken.objects.filter(doctor=doctor)).select_related(
        "patient", "doctor__user", "appointment"
    )


@method_decorator(role_required("receptionist", "admin"), name="dispatch")
class ReceptionQueueView(LoginRequiredMixin, FormView):
    template_name = "queue/reception.html"
    form_class = ReceptionTokenForm

    def form_valid(self, form):
        user_model = get_user_model()
        patient = form.cleaned_data.get("existing_patient")
        if not patient:
            base_username = form.cleaned_data["new_username"].strip()
            username = base_username
            idx = 1
            while user_model.objects.filter(username=username).exists():
                idx += 1
                username = f"{base_username}{idx}"
            patient = user_model.objects.create_user(
                username=username,
                password=DEFAULT_PATIENT_PASSWORD,
                role="patient",
                first_name=form.cleaned_data.get("new_first_name", ""),
                last_name=form.cleaned_data.get("new_last_name", ""),
                email=form.cleaned_data.get("new_email", ""),
                phone=form.cleaned_data.get("new_phone", ""),
            )

        PatientProfile.objects.get_or_create(user=patient)
        token = QueueService.create_walk_in_token(
            doctor=form.cleaned_data["doctor"],
            patient=patient,
            notes=form.cleaned_data.get("notes", ""),
        )
        messages.success(
            self.request,
            f"Token created: {token.token_display}. Default password for new patient is {DEFAULT_PATIENT_PASSWORD}.",
        )
        return redirect(f"/reception/?doctor={token.doctor_id}")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor_id = self.request.GET.get("doctor")
        selected_doctor = Doctor.objects.filter(id=doctor_id).first() if doctor_id else None
        if selected_doctor:
            tokens = _queue_for_doctor_today(selected_doctor).order_by("-priority", "token_number")
        else:
            tokens = filter_today(
                QueueToken.objects.all()
            ).select_related("patient", "doctor__user", "appointment").order_by(
                "doctor__user__first_name", "-priority", "token_number"
            )
        context.update(
            {
                "doctors": Doctor.objects.select_related("user").order_by("user__first_name", "user__username"),
                "available_doctor_count": Doctor.objects.filter(is_available=True).count(),
                "selected_doctor": selected_doctor,
                "tokens": tokens,
            }
        )
        return context


@method_decorator(role_required("receptionist", "admin"), name="dispatch")
class ReceptionActionView(LoginRequiredMixin, View):
    def post(self, request, token_id, action):
        messages.info(request, "Reception queue is view-only in this workflow.")
        return redirect("web-reception-queue")


@method_decorator(role_required("receptionist", "admin"), name="dispatch")
class ReceptionCallNextView(LoginRequiredMixin, View):
    def post(self, request, doctor_id):
        messages.info(request, "Only doctor can call the next patient.")
        return redirect("web-reception-queue")


@method_decorator(role_required("doctor"), name="dispatch")
class DoctorQueueView(LoginRequiredMixin, TemplateView):
    template_name = "queue/doctor_queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = get_object_or_404(Doctor, user=self.request.user)
        queue = _queue_for_doctor_today(doctor).order_by("-priority", "token_number")
        current = queue.filter(status__in=["called", "in_consultation"]).first()
        waiting = queue.filter(status="waiting")
        prescribed_appointments = set(
            Prescription.objects.filter(doctor=doctor, appointment__in=queue.values("appointment_id")).values_list(
                "appointment_id", flat=True
            )
        )
        current_prescription = (
            Prescription.objects.filter(doctor=doctor, appointment=current.appointment).first()
            if current and current.appointment
            else None
        )
        last_prescription_id = self.request.session.get("last_completed_prescription_id")
        last_completed_prescription = (
            Prescription.objects.filter(id=last_prescription_id, doctor=doctor).first()
            if last_prescription_id
            else None
        )
        current_patient_profile = (
            PatientProfile.objects.filter(user=current.patient).first() if current else None
        )
        current_patient_history = {
            "appointments": Appointment.objects.filter(patient=current.patient).select_related("doctor__user")[:8]
            if current
            else [],
            "prescriptions": Prescription.objects.filter(patient=current.patient, doctor=doctor).order_by("-created_at")[:8]
            if current
            else [],
            "visits": PatientVisit.objects.filter(patient=current.patient, doctor=doctor).order_by("-visit_date")[:8]
            if current
            else [],
        }
        context.update(
            {
                "doctor": doctor,
                "current": current,
                "waiting": waiting,
                "completed": queue.filter(status="completed")[:10],
                "current_has_prescription": bool(
                    current and current.appointment_id and current.appointment_id in prescribed_appointments
                ),
                "current_prescription": current_prescription,
                "last_completed_prescription": last_completed_prescription,
                "current_patient_profile": current_patient_profile,
                "current_patient_history": current_patient_history,
            }
        )
        return context


@method_decorator(role_required("doctor"), name="dispatch")
class DoctorTokenActionView(LoginRequiredMixin, View):
    def post(self, request, token_id, action):
        doctor = get_object_or_404(Doctor, user=request.user)
        token = get_object_or_404(QueueToken, id=token_id, doctor=doctor)

        if action == "call":
            if token.status != "waiting":
                messages.info(request, f"{token.token_display} is not in waiting state.")
                return redirect("web-doctor-queue")
            active_exists = _queue_for_doctor_today(doctor).filter(status__in=["called", "in_consultation"]).exclude(
                id=token.id
            ).exists()
            if active_exists:
                messages.info(request, "Finish current patient before calling another.")
                return redirect("web-doctor-queue")
            token.status = "called"
            token.called_time = timezone.now()
            token.save(update_fields=["status", "called_time", "updated_at"])
            messages.success(request, f"Called {token.token_display}")
        elif action == "start":
            if token.status not in ["called"]:
                messages.info(request, f"{token.token_display} must be called first.")
                return redirect("web-doctor-queue")
            QueueService.start_consultation(token)
            messages.success(request, f"Consultation started for {token.token_display}")
        elif action == "complete":
            if token.status not in ["in_consultation", "called"]:
                messages.info(request, f"{token.token_display} cannot be completed now.")
                return redirect("web-doctor-queue")
            if not token.appointment:
                messages.error(request, "Add prescription first, then end consultation.")
                return redirect("web-doctor-queue")
            prescription = Prescription.objects.filter(appointment=token.appointment, doctor=doctor).first()
            if not prescription:
                messages.error(request, "Add prescription before ending consultation.")
                return redirect("web-doctor-queue")

            emailed = PrescriptionService.email_prescription_to_patient(prescription)
            prescription.email_sent = bool(emailed)
            prescription.emailed_at = timezone.now() if emailed else None
            prescription.save(update_fields=["email_sent", "emailed_at", "updated_at"])
            QueueService.complete_consultation(token)
            bill, _ = BillingService.create_or_get_bill_for_appointment(token.appointment)
            request.session["last_completed_prescription_id"] = prescription.id
            if emailed:
                messages.success(
                    request,
                    f"Consultation completed for {token.token_display}. Prescription sent. "
                    f"Bill generated: {bill.bill_number if bill else 'N/A'}",
                )
            else:
                messages.warning(
                    request,
                    f"Consultation completed for {token.token_display}. Prescription saved (email not sent). "
                    f"Bill generated: {bill.bill_number if bill else 'N/A'}",
                )
        return redirect("web-doctor-queue")


@method_decorator(role_required("doctor"), name="dispatch")
class DoctorCallNextView(LoginRequiredMixin, View):
    def post(self, request):
        doctor = get_object_or_404(Doctor, user=request.user)
        next_token = QueueService.call_next_patient(doctor)
        if next_token:
            messages.success(request, f"Called next patient: {next_token.token_display}")
        else:
            has_active = _queue_for_doctor_today(doctor).filter(status__in=["called", "in_consultation"]).exists()
            if has_active:
                messages.info(request, "Finish current patient before calling next.")
            else:
                messages.info(request, "No waiting patients.")
        return redirect("web-doctor-queue")


@method_decorator(role_required("doctor"), name="dispatch")
class AddPrescriptionView(LoginRequiredMixin, FormView):
    template_name = "billing/add_prescription.html"
    form_class = PrescriptionForm

    def dispatch(self, request, *args, **kwargs):
        self.token = get_object_or_404(QueueToken, id=kwargs["token_id"])
        doctor = get_object_or_404(Doctor, user=request.user)
        if self.token.doctor != doctor:
            messages.error(request, "Not allowed.")
            return redirect("web-doctor-queue")
        if self.token.status not in ["called", "in_consultation"]:
            messages.error(request, "Prescription can be added only for called/in-consultation patient.")
            return redirect("web-doctor-queue")
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        doctor = get_object_or_404(Doctor, user=self.request.user)
        if self.token.appointment:
            existing = Prescription.objects.filter(appointment=self.token.appointment, doctor=doctor).first()
            if existing:
                initial.update(
                    {
                        "symptoms": existing.symptoms,
                        "diagnosis": existing.diagnosis,
                        "medicines": existing.medicines,
                        "dosage": existing.dosage,
                        "notes": existing.notes,
                        "follow_up_date": existing.follow_up_date,
                    }
                )
        return initial

    def _extract_medicine_rows(self):
        def to_pos_int(value, default=1):
            try:
                parsed = int(value)
                return parsed if parsed > 0 else default
            except Exception:
                return default

        names = self.request.POST.getlist("medicine_name[]")
        doses = self.request.POST.getlist("medicine_dose[]")
        times = self.request.POST.getlist("medicine_times[]")
        days = self.request.POST.getlist("medicine_days[]")
        qtys = self.request.POST.getlist("medicine_qty[]")
        timings = self.request.POST.getlist("medicine_timing[]")
        instructions = self.request.POST.getlist("medicine_instruction[]")

        rows = []
        size = len(names)
        for i in range(size):
            name = (names[i] or "").strip()
            if not name:
                continue
            row = {
                "medicine_name": name,
                "dose": (doses[i] if i < len(doses) else "").strip(),
                "times_per_day": to_pos_int(times[i] if i < len(times) else 1, default=1),
                "duration_days": to_pos_int(days[i] if i < len(days) else 1, default=1),
                "quantity_tablets": to_pos_int(qtys[i] if i < len(qtys) else 1, default=1),
                "timing": (timings[i] if i < len(timings) else "after_food"),
                "instruction": (instructions[i] if i < len(instructions) else "").strip(),
            }
            rows.append(row)
        return rows

    def form_valid(self, form):
        doctor = get_object_or_404(Doctor, user=self.request.user)
        if not self.token.appointment:
            # For walk-ins, auto-create an appointment record so prescription can be stored.
            appointment = Appointment.objects.create(
                patient=self.token.patient,
                doctor=self.token.doctor,
                status="confirmed",
                notes=self.token.notes or "Walk-in consultation",
                is_walk_in=True,
            )
            self.token.appointment = appointment
            self.token.save(update_fields=["appointment", "updated_at"])

        medicine_rows = self._extract_medicine_rows()
        if not medicine_rows:
            form.add_error(None, "Add at least one medicine row.")
            return self.form_invalid(form)

        prescription = Prescription.objects.filter(appointment=self.token.appointment, doctor=doctor).first()
        if prescription:
            for field, value in form.cleaned_data.items():
                setattr(prescription, field, value)
        else:
            prescription = form.save(commit=False)
            prescription.appointment = self.token.appointment
            prescription.doctor = doctor
            prescription.patient = self.token.patient
        summary_lines = []
        for index, row in enumerate(medicine_rows, start=1):
            summary_lines.append(
                f"{index}. {row['medicine_name']} | {row['dose'] or '-'} | {row['times_per_day']}x/day | "
                f"{row['duration_days']} days | {row['quantity_tablets']} tablets | {row['timing']} | "
                f"{row['instruction'] or '-'}"
            )
        prescription.medicines = "\n".join(summary_lines)
        prescription.save()
        prescription.medicine_items.all().delete()
        for idx, row in enumerate(medicine_rows):
            PrescriptionMedicine.objects.create(
                prescription=prescription,
                medicine_name=row["medicine_name"],
                dose=row["dose"],
                times_per_day=row["times_per_day"],
                duration_days=row["duration_days"],
                quantity_tablets=row["quantity_tablets"],
                timing=row["timing"],
                instruction=row["instruction"],
                sort_order=idx,
            )

        emailed = PrescriptionService.email_prescription_to_patient(prescription)
        if emailed:
            messages.success(self.request, "Prescription saved and emailed to patient.")
        else:
            messages.warning(self.request, "Prescription saved. Email not sent (check SMTP/patient email).")
        return redirect("web-doctor-queue")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["token"] = self.token
        doctor = get_object_or_404(Doctor, user=self.request.user)
        prescription = (
            Prescription.objects.filter(appointment=self.token.appointment, doctor=doctor).first()
            if self.token.appointment
            else None
        )
        context["medicine_items"] = list(prescription.medicine_items.all()) if prescription else []
        return context


class QueueDisplayView(TemplateView):
    template_name = "queue/display.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctor = get_object_or_404(Doctor, id=self.kwargs["doctor_id"])
        context.update({"doctor": doctor})
        return context


@method_decorator(role_required("receptionist", "admin"), name="dispatch")
class TVLauncherView(LoginRequiredMixin, TemplateView):
    template_name = "queue/tv_launcher.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        doctors = Doctor.objects.select_related("user").order_by("user__first_name", "user__username")
        context["doctor_links"] = [
            {
                "doctor": d,
                "display_url": self.request.build_absolute_uri(f"/display/{d.id}/"),
            }
            for d in doctors
        ]
        return context


class QueueDisplayDataView(View):
    def get(self, request, doctor_id):
        doctor = get_object_or_404(Doctor, id=doctor_id)
        current = filter_today(
            QueueToken.objects.filter(
                doctor=doctor,
                status__in=["called", "in_consultation"],
            )
        ).order_by("-priority", "token_number").first()
        waiting = filter_today(QueueToken.objects.filter(
            doctor=doctor,
            status="waiting",
        )).order_by("-priority", "token_number")[:8]

        return JsonResponse(
            {
                "doctor": f"Dr. {doctor.user.get_full_name() or doctor.user.username}",
                "current": {
                    "token": current.token_display,
                    "status": current.status,
                }
                if current
                else None,
                "waiting": [{"token": t.token_display, "status": t.status} for t in waiting],
                "updated_at": timezone.now().isoformat(),
            }
        )
