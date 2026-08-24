import time

from django.core.management.base import BaseCommand

from clinic.services.notifications import (
    process_pending_jobs,
    queue_due_medication_reminders,
)


class Command(BaseCommand):
    help = "Processes pending CareCompass notification jobs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Continue processing jobs every 60 seconds."
        )

    def handle(self, *args, **options):
        while True:
            queue_due_medication_reminders()
            process_pending_jobs()
            self.stdout.write(
                self.style.SUCCESS("Notification jobs checked.")
            )

            if not options["loop"]:
                break

            time.sleep(60)