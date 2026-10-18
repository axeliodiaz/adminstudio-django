"""Rebuild every precomputed report table (CYC-441).

Runs on each deploy from render_start.sh with --resume (no cron on the free
tier) and can be run by hand: ``python manage.py refresh_reports``. Between
deploys the post_save signals and the explicit bulk-update hooks keep rows
fresh. Newest days are rebuilt first so recent history lands early; --resume
skips days that already have rows, which lets an interrupted backfill pick
up where it stopped on the next deploy.
"""

from django.core.management.base import BaseCommand

from apps.reports import services


class Command(BaseCommand):
    help = "Rebuild the precomputed report tables (DailyMetrics, ClassMetrics)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Skip days that already have a DailyMetrics row.",
        )

    def handle(self, *args, **options):
        summary = services.refresh_all(skip_existing=options["resume"])
        self.stdout.write(
            self.style.SUCCESS(
                "refresh_reports: {days_recomputed} days "
                "({first_day} → {last_day}), {classes_recomputed} classes.".format(**summary)
            )
        )
