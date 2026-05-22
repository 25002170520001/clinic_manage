from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "Load the repository backup fixture (data.json) into the current database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--fixture",
            default="data.json",
            help="Fixture file to load relative to the project root.",
        )

    def handle(self, *args, **options):
        fixture_path = Path(settings.BASE_DIR) / options["fixture"]
        if not fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {fixture_path}")

        self.stdout.write(self.style.WARNING(f"Loading fixture: {fixture_path}"))
        call_command("loaddata", str(fixture_path))
        self.stdout.write(self.style.SUCCESS("Backup data loaded successfully."))