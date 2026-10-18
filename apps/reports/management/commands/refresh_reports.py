"""Rebuild every precomputed report table (CYC-441).

Runs on each deploy from render_start.sh (no cron on the free tier) and can
be run by hand: ``python manage.py refresh_reports``. Between deploys the
post_save signals and the explicit bulk-update hooks keep rows fresh.
"""

from django.core.management.base import BaseCommand

from apps.reports import services


class Command(BaseCommand):
    help = "Rebuild the precomputed report tables (DailyMetrics, ClassMetrics)."

    def handle(self, *args, **options):
        summary = services.refresh_all()
        self.stdout.write(
            self.style.SUCCESS(
                "refresh_reports: {days_recomputed} days "
                "({first_day} → {last_day}), {classes_recomputed} classes.".format(**summary)
            )
        )
