from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = "Send a test email to specified address (or DEFAULT_FROM_EMAIL)."

    def add_arguments(self, parser):
        parser.add_argument(
            "to",
            nargs="?",
            help="Recipient email address",
            default=None,
        )

    def handle(self, *args, **options):
        to = options.get("to") or settings.DEFAULT_FROM_EMAIL
        subject = "Test email from clinic_manage"
        message = "This is a test email sent from the clinic_manage app."
        from_email = settings.DEFAULT_FROM_EMAIL
        send_mail(subject, message, from_email, [to])
        self.stdout.write(self.style.SUCCESS(f"Sent test email to {to} using backend {settings.EMAIL_BACKEND}"))
