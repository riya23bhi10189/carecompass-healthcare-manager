from django.core.management.base import BaseCommand

from clinic.services.calendar import get_calendar_service


class Command(BaseCommand):
    help = "Authorizes a Google account for CareCompass Calendar."

    def handle(self, *args, **options):
        get_calendar_service(interactive=True)

        self.stdout.write(
            self.style.SUCCESS(
                "Google Calendar authorized successfully. token.json was created."
            )
        )