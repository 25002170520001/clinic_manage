from django.utils import timezone
from django.db.models import F

from .models import PatientVisit, QueueToken
from .time_utils import filter_today


class QueueService:
    """Service layer for queue token workflows."""

    @staticmethod
    def _next_token_number_for_doctor(doctor):
        last_token = filter_today(QueueToken.objects.filter(doctor=doctor)).order_by("-token_number").first()
        return (last_token.token_number + 1) if last_token else 1

    @staticmethod
    def generate_token_for_appointment(appointment):
        token_number = QueueService._next_token_number_for_doctor(appointment.doctor)
        token_display = f"A-{token_number:02d}"

        return QueueToken.objects.create(
            token_number=token_number,
            token_display=token_display,
            priority=2,
            patient=appointment.patient,
            doctor=appointment.doctor,
            appointment=appointment,
            status="waiting",
            notes=appointment.notes,
        )

    @staticmethod
    def create_walk_in_token(doctor, patient, notes=""):
        token_number = QueueService._next_token_number_for_doctor(doctor)
        token_display = f"W-{token_number:02d}"

        token = QueueToken.objects.create(
            token_number=token_number,
            token_display=token_display,
            priority=1,
            patient=patient,
            doctor=doctor,
            status="waiting",
            is_walk_in=True,
            notes=notes,
        )
        QueueService.register_visit(patient=patient, doctor=doctor)
        return token

    @staticmethod
    def get_next_patient(doctor):
        return filter_today(
            QueueToken.objects.filter(
                doctor=doctor,
                status="waiting",
            )
        ).order_by("-priority", "token_number", "created_at").first()

    @staticmethod
    def call_next_patient(doctor):
        # If someone is already called or in consultation, do not pull another token.
        active = filter_today(
            QueueToken.objects.filter(
                doctor=doctor,
                status__in=["called", "in_consultation"],
            )
        ).exists()
        if active:
            return None

        token = QueueService.get_next_patient(doctor)
        if not token:
            return None
        token.status = "called"
        token.called_time = timezone.now()
        token.save(update_fields=["status", "called_time", "updated_at"])
        return token

    @staticmethod
    def start_consultation(token):
        token.status = "in_consultation"
        token.consultation_start_time = timezone.now()
        token.save(update_fields=["status", "consultation_start_time", "updated_at"])
        return token

    @staticmethod
    def complete_consultation(token):
        token.status = "completed"
        token.consultation_end_time = timezone.now()
        token.save(update_fields=["status", "consultation_end_time", "updated_at"])
        if token.appointment:
            token.appointment.status = "completed"
            token.appointment.save(update_fields=["status", "updated_at"])
        return token

    @staticmethod
    def check_in_token(token):
        token.arrival_time = timezone.now()
        update_fields = ["arrival_time", "updated_at"]

        # Anti-cheat: if patient appears before online booking time, downgrade to walk-in.
        if token.appointment and token.arrival_time < token.appointment.booking_time:
            token.priority = 1
            token.is_walk_in = True
            if token.token_display.startswith("A-"):
                token.token_display = f"W-{token.token_number:02d}"
            token.appointment.is_walk_in = True
            token.appointment.save(update_fields=["is_walk_in", "updated_at"])
            update_fields.extend(["priority", "is_walk_in", "token_display"])

        token.save(update_fields=update_fields)
        QueueService.register_visit(patient=token.patient, doctor=token.doctor, when=token.arrival_time)
        return token

    @staticmethod
    def register_visit(patient, doctor, when=None):
        when = when or timezone.now()
        visit_date = timezone.localdate(when)
        visit, created = PatientVisit.objects.get_or_create(
            patient=patient,
            doctor=doctor,
            visit_date=visit_date,
            defaults={
                "first_seen_at": when,
                "last_seen_at": when,
                "check_in_count": 1,
            },
        )
        if not created:
            PatientVisit.objects.filter(id=visit.id).update(
                last_seen_at=when,
                check_in_count=F("check_in_count") + 1,
            )
            visit.refresh_from_db(fields=["last_seen_at", "check_in_count"])
        return visit
