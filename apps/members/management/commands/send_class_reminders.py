"""Day-before reminder emails for members with a reservation tomorrow (CYC-5)."""

from datetime import datetime, time, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.members import constants
from apps.members.models import Reservation
from apps.notifications.email_templates import render_class_reminder
from apps.notifications.services import create_notification
from apps.schedules.constants import SCHEDULE_STATUS_CANCELED, SCHEDULE_STATUS_DRAFT


def _send_reminder(reservation) -> bool:
    user = reservation.member.user
    if not user.email:
        return False
    schedule = reservation.schedule
    local_start = timezone.localtime(schedule.start_time)
    time_label = f"{local_start.hour}:{local_start.minute:02d}"
    title = schedule.title or "clase"
    instructor_user = schedule.instructor.user
    instructor_name = instructor_user.get_full_name() or instructor_user.username
    instructor_short = instructor_user.first_name or instructor_name
    room = schedule.room
    studio_name = room.studio.name if room and room.studio else ""
    room_name = room.name if room else ""
    frontend_url = (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip("/")
    action_url = f"{frontend_url}/#my-reservations"
    subject = f"Ma\\u00f1ana a las {time_label} \\u00b7 {title} con {instructor_short}"
    when_label = local_start.strftime("%d/%m/%Y %H:%M")
    message = (
        f"Recordatorio de tu clase {title} con {instructor_name} "
        f"el {when_label}"
        + (f" en {studio_name} \\u00b7 {room_name}" if studio_name or room_name else "")
        + (f", spot {reservation.spot}." if reservation.spot else ".")
        + " Lleva zapatillas de ciclismo y una toalla."
    )
    create_notification(
        subject,
        message,
        [user],
        html_content=render_class_reminder(
            class_title=title,
            time_label=time_label,
            instructor_name=instructor_name,
            studio_name=studio_name,
            room_name=room_name,
            spot=reservation.spot,
            action_url=action_url,
            frontend_url=frontend_url,
        ),
    )
    reservation.reminder_sent_at = timezone.now()
    reservation.save(update_fields=["reminder_sent_at", "modified"])
    return True


class Command(BaseCommand):
    help = "Email members a reminder the day before their reserved class."

    def handle(self, *args, **options):
        tomorrow = timezone.localdate() + timedelta(days=1)
        start_dt = timezone.make_aware(datetime.combine(tomorrow, time.min))
        end_dt = timezone.make_aware(datetime.combine(tomorrow, time.max))
        reservations = (
            Reservation.objects.filter(
                is_removed=False,
                status=constants.RESERVATION_STATUS_RESERVED,
                reminder_sent_at__isnull=True,
                schedule__is_removed=False,
                schedule__start_time__gte=start_dt,
                schedule__start_time__lte=end_dt,
            )
            .exclude(schedule__status__in=[SCHEDULE_STATUS_DRAFT, SCHEDULE_STATUS_CANCELED])
            .select_related("member__user", "schedule__instructor__user", "schedule__room__studio")
        )
        sent = 0
        for reservation in reservations:
            if _send_reminder(reservation):
                sent += 1
        self.stdout.write(self.style.SUCCESS(f"Class reminders sent: {sent}"))
