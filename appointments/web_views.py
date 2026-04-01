from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import FormView, TemplateView

from accounts.decorators import role_required
from token_queue.models import QueueToken

from .forms import AppointmentBookingForm
from .models import Appointment
from .services.booking_service import AppointmentBookingService


@method_decorator(role_required("patient"), name="dispatch")
class PatientBookAppointmentView(LoginRequiredMixin, FormView):
    template_name = "appointments/book.html"
    form_class = AppointmentBookingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["doctor_count"] = self.get_form().fields["doctor"].queryset.count()
        return context

    def form_valid(self, form):
        appointment, token = AppointmentBookingService.book_without_slot(
            patient=self.request.user,
            doctor=form.cleaned_data["doctor"],
            notes=form.cleaned_data.get("notes", ""),
        )
        messages.success(
            self.request,
            f"Appointment booked. Your token is {token.token_display}.",
        )
        return redirect("patient-appointments")


@method_decorator(role_required("patient"), name="dispatch")
class PatientAppointmentListView(LoginRequiredMixin, TemplateView):
    template_name = "appointments/my_appointments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        appointments = Appointment.objects.filter(patient=self.request.user).select_related("doctor__user")
        tokens = QueueToken.objects.filter(patient=self.request.user).select_related("doctor__user", "appointment")
        context.update(
            {
                "appointments": appointments,
                "active_token": tokens.filter(status__in=["waiting", "called", "in_consultation"]).first(),
            }
        )
        return context


@method_decorator(role_required("patient"), name="dispatch")
class CancelAppointmentView(LoginRequiredMixin, View):
    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk, patient=request.user)
        if appointment.status == "completed":
            messages.error(request, "Completed appointments cannot be cancelled.")
            return redirect("patient-appointments")

        appointment.status = "cancelled"
        appointment.save(update_fields=["status", "updated_at"])
        QueueToken.objects.filter(appointment=appointment, status="waiting").update(status="cancelled")
        messages.success(request, "Appointment cancelled.")
        return redirect("patient-appointments")
