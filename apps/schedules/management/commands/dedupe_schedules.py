"""Soft-delete duplicated schedule copies (CYC-91).

Groups active schedules by (room, start_time, title) and keeps one copy per
group: the one with the most active reservations, breaking ties toward the
oldest. Every other copy and its reservations are soft-deleted.

Dry-run by default; pass --apply to make the changes.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.members.models import Reservation
from apps.schedules.models import Schedule


class Command(BaseCommand):
    help = "Soft-delete duplicated schedules, keeping one per (room, start_time, title)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the soft-deletes. Without this flag the command only reports.",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        groups = defaultdict(list)
        for schedule in Schedule.objects.filter(is_removed=False).order_by("created"):
            key = (schedule.room_id, schedule.start_time, schedule.title)
            groups[key].append(schedule)

        duplicates = {key: items for key, items in groups.items() if len(items) > 1}
        self.stdout.write(f"Groups with duplicates: {len(duplicates)} (of {len(groups)})")

        removed_schedules = 0
        removed_reservations = 0
        ordered = sorted(duplicates.items(), key=lambda pair: (pair[0][1], pair[0][2]))
        for (room_id, start_time, title), items in ordered:
            counts = {
                item.id: Reservation.objects.filter(schedule=item, is_removed=False).count()
                for item in items
            }
            keep = max(items, key=lambda item: (counts[item.id], -item.created.timestamp()))
            losers = [item for item in items if item.id != keep.id]
            loser_reservations = sum(counts[item.id] for item in losers)
            self.stdout.write(
                f"{start_time:%Y-%m-%d %H:%M} | {title} | keep {keep.id} "
                f"({counts[keep.id]} reservations) | remove {len(losers)} copies "
                f"({loser_reservations} reservations)"
            )
            if apply_changes:
                with transaction.atomic():
                    for loser in losers:
                        for reservation in Reservation.objects.filter(
                            schedule=loser, is_removed=False
                        ):
                            reservation.delete()
                        loser.delete()
            removed_schedules += len(losers)
            removed_reservations += loser_reservations

        verb = "Soft-deleted" if apply_changes else "Would soft-delete"
        self.stdout.write(
            self.style.SUCCESS(
                f"{verb} {removed_schedules} duplicated schedules and "
                f"{removed_reservations} reservations. Wallet credits are not adjusted."
            )
        )
        if not apply_changes:
            self.stdout.write("Dry run. Re-run with --apply to make the changes.")
