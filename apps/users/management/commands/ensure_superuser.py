"""Ensure a Django superuser exists from env vars (non-interactive).

Used on Render free (no Shell/SSH). Password is applied only when the user
is created so later admin password changes are not overwritten on restart.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create a superuser from DJANGO_SUPERUSER_* env vars if missing."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")

        if not username or not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping ensure_superuser: set DJANGO_SUPERUSER_USERNAME, "
                    "DJANGO_SUPERUSER_EMAIL, and DJANGO_SUPERUSER_PASSWORD."
                )
            )
            return

        user = User.objects.filter(username=username).first()
        if user is None:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Created superuser {username!r}."))
            return

        changed = False
        if not user.is_superuser or not user.is_staff:
            user.is_superuser = True
            user.is_staff = True
            changed = True
        if email and user.email != email:
            user.email = email
            changed = True
        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Updated flags/email for {username!r}."))
        else:
            self.stdout.write(f"Superuser {username!r} already present.")
