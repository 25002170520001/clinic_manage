from appointments.models import Appointment
from token_queue.services import QueueService


class AppointmentBookingService:
    @staticmethod
    def book_without_slot(patient, doctor, notes=""):
        appointment = Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            notes=notes,
            status="pending",
        )
        token = QueueService.generate_token_for_appointment(appointment)
        return appointment, token
