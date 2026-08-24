import os

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from clinic.models import Profile


class Command(BaseCommand):
    help = "Create or update the CareCompass admin account"

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME", "admin")
        password = os.getenv("ADMIN_PASSWORD")
        email = os.getenv("ADMIN_EMAIL", "")

        if not password:
            self.stdout.write(
                self.style.ERROR(
                    "ADMIN_PASSWORD environment variable is not set."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )

        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile.role = "ADMIN"
        profile.save()

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Admin user '{username}' created successfully."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Admin user '{username}' updated successfully."
                )
            )