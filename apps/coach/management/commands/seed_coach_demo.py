"""Seed PulseFit coach calendars, rosters, notes and playlists.

Idempotent. Demo rows are tagged with `demo.coach` in Schedule.description
and celebrity usernames from the shared catalog. Showcase coach is Kristina Girod.

Default horizon: 1 January of last year through the last day of February next year,
so every instructor (including existing staff like Axel) has classes to
open in Clases del día, Mi horario, Lista de riders, Notas, Playlist and
Estadísticas. `--reset` only removes demo.coach.* leftover users and
schedules marked demo.coach (plus related reservations/playlists/ratings).
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from random import Random
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from apps.coach.constants import (
    DEMO_CLASS_DESCRIPTION,
    DEMO_EVENT_DESCRIPTION,
    DEMO_SHOWCASE_USERNAME,
    DEMO_USERNAME_PREFIX,
)
from apps.coach.models import (
    ClassPlaylist,
    ClassRating,
    PlaylistSegment,
    PlaylistTemplate,
    PlaylistTrack,
)
from apps.instructors.models import Instructor
from apps.members import constants as member_constants
from apps.members.models import Member, Reservation, WaitlistEntry
from apps.notifications.models import Notification
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.studios.models import Address, Room, Studio
from apps.users.demo_catalog import (
    FUN_CLASS_BLURBS,
    FUN_RIDER_NOTES,
    MEMBERS as CELEBRITY_MEMBERS,
    SPECIAL_EVENTS,
    coach_seed_end,
    coach_seed_start,
)

User = get_user_model()
SANTIAGO = ZoneInfo("America/Santiago")
FIRST_TIMER_COUNT = 4
ROSTER_SIZE = 18

WEEKDAY_PATTERNS = (
    ((7, "Power Ride"), (19, "HIIT Ride")),
    ((6, "Sunrise Ride"), (18, "After Work")),
    ((8, "Morning Climb"), (20, "Night Power")),
    ((9, "RIDE 45"), (12, "Midday HIIT")),
    ((7, "POWER 45"), (18, "SCULPT Ride")),
)
WEEKEND_PATTERNS = (
    ((9, "Weekend Ride"), (18, "Sunset Ride")),
    ((10, "Brunch Ride"), (17, "Late Weekend")),
)

POWER_PLAYLIST_SEGMENTS = [
    (
        "Warm-up",
        8,
        "120-128",
        [
            ("Midnight City", "M83", 105, 241),
            ("Blinding Lights", "The Weeknd", 171, 200),
        ],
    ),
    (
        "Climb 1",
        10,
        "140-150",
        [
            ("Titanium", "David Guetta ft. Sia", 126, 245),
            ("Stronger", "Kanye West", 104, 312),
        ],
    ),
    (
        "Sprints",
        12,
        "160-175",
        [
            ("Can't Hold Us", "Macklemore & Ryan Lewis", 146, 258),
            ("Levels", "Avicii", 126, 202),
        ],
    ),
    (
        "Recovery",
        8,
        "110-120",
        [("Sunset Lover", "Petit Biscuit", 91, 237)],
    ),
    (
        "Cool-down",
        7,
        "90-100",
        [("Holocene", "Bon Iver", 136, 337)],
    ),
]

HIIT_PLAYLIST_SEGMENTS = [
    (
        "Activation",
        6,
        "118-125",
        [("Don't Start Now", "Dua Lipa", 124, 183)],
    ),
    (
        "Block 1",
        12,
        "150-165",
        [
            ("Physical", "Dua Lipa", 147, 194),
            ("On My Mind", "Diplo & SIDEPIECE", 124, 174),
        ],
    ),
    (
        "Block 2",
        12,
        "160-175",
        [("Piece of Your Heart", "MEDUZA", 124, 153)],
    ),
    (
        "Break",
        6,
        "110-120",
        [("Nightcall", "Kavinsky", 91, 257)],
    ),
    (
        "Cool-down",
        9,
        "90-100",
        [("Sunset Lover", "Petit Biscuit", 91, 237)],
    ),
]


def _aware(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SANTIAGO)


class Command(BaseCommand):
    help = (
        "Create PulseFit coach calendars, events, rosters, playlists and ratings "
        "from last January through February of next year."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previous demo.coach rows before seeding.",
        )
        parser.add_argument(
            "--as-of",
            help="Pretend today is this date (YYYY-MM-DD). Defaults to the local date.",
        )
        parser.add_argument(
            "--from-date",
            dest="from_date",
            help="First calendar day to seed (YYYY-MM-DD). Defaults to 1 January of last year.",
        )
        parser.add_argument(
            "--until",
            help="Last calendar day to seed (YYYY-MM-DD). Defaults to end of February next year.",
        )

    def handle(self, *args, **options):
        rng = Random(7)
        if options["reset"]:
            self._wipe()
            self.stdout.write(self.style.WARNING("Removed previous coach demo data."))
        call_command("seed_demo_catalog", verbosity=options["verbosity"])

        today = (
            date.fromisoformat(options["as_of"])
            if options["as_of"]
            else timezone.now().astimezone(SANTIAGO).date()
        )
        start_day = (
            date.fromisoformat(options["from_date"])
            if options["from_date"]
            else coach_seed_start(today)
        )
        end_day = (
            date.fromisoformat(options["until"]) if options["until"] else coach_seed_end(today)
        )
        if start_day > end_day:
            start_day = end_day

        room = self._room()
        event_room = Room.objects.filter(name__icontains="Eventos").first() or room
        instructors = self._instructors()
        riders = self._riders()

        created_total = 0
        for index, instructor in enumerate(instructors):
            self._templates(instructor, extra=(index % 3 == 0))
            weekday = WEEKDAY_PATTERNS[index % len(WEEKDAY_PATTERNS)]
            weekend = WEEKEND_PATTERNS[index % len(WEEKEND_PATTERNS)]
            new_schedules = self._ensure_schedules(
                instructor, room, weekday, weekend, start_day, end_day, today
            )
            if new_schedules:
                self._fill(
                    Random(f"roster:{instructor.user.username}"),
                    room,
                    riders,
                    new_schedules,
                    today,
                )
                created_total += len(new_schedules)
            self._backfill_playlists(instructor)
            self._backfill_ratings(Random(f"rating:{instructor.user.username}"), instructor)

        created_total += self._ensure_events(instructors, event_room, start_day, end_day, today)
        self._waitlists(rng, riders, today)
        self._notifications(rng, riders)

        names = ", ".join(item.user.username for item in instructors[:8])
        extra = f" (+{len(instructors) - 8})" if len(instructors) > 8 else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded coach demo {start_day.isoformat()} → {end_day.isoformat()}: "
                f"{len(instructors)} coaches ({names}{extra}), "
                f"{created_total} nuevas clases. Login Kristina: "
                f"{DEMO_SHOWCASE_USERNAME} / demo1234"
            )
        )

    def _wipe(self):
        demo_schedules = Schedule.objects.filter(description__startswith="demo.coach")
        ClassRating.objects.filter(schedule__in=demo_schedules).delete()
        ClassPlaylist.objects.filter(schedule__in=demo_schedules).delete()
        WaitlistEntry.objects.filter(schedule__in=demo_schedules).delete()
        Reservation.objects.filter(schedule__in=demo_schedules).delete()
        demo_schedules.delete()
        Notification.objects.filter(subject__startswith="[demo.coach]").delete()

        demo_users = User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
        PlaylistTemplate.objects.filter(instructor__user__in=demo_users).delete()
        Reservation.objects.filter(member__user__in=demo_users).delete()
        Instructor.objects.filter(user__in=demo_users).delete()
        Member.objects.filter(user__in=demo_users).delete()
        demo_users.delete()

    def _room(self):
        studio = Studio.objects.filter(name__icontains="PulseFit").order_by("created").first()
        if studio is None:
            address, _ = Address.objects.get_or_create(address="Camino El Alba 12345, Las Condes")
            studio, _ = Studio.objects.get_or_create(
                name="PulseFit",
                defaults={"address": address, "is_active": True},
            )
        room = Room.objects.filter(studio=studio, name="Sala A").first()
        if room is None:
            room = Room.objects.filter(name="Sala A").first()
        if room is None:
            room = Room.objects.create(studio=studio, name="Sala A", capacity=40, is_active=True)
        return room

    def _instructors(self):
        by_id = {}
        staff_users = User.objects.filter(is_removed=False, is_active=True, is_staff=True)
        for user in staff_users:
            instructor, created = Instructor.objects.get_or_create(user=user)
            if created and not instructor.tagline:
                instructor.tagline = "Indoor cycling"
                instructor.specialties = ["Ride"]
                instructor.languages = ["Español"]
                instructor.save()
            by_id[str(instructor.id)] = instructor
        for instructor in Instructor.objects.filter(is_removed=False).select_related("user"):
            by_id[str(instructor.id)] = instructor
        return sorted(by_id.values(), key=lambda item: item.user.username)

    def _riders(self):
        names = [persona.username for persona in CELEBRITY_MEMBERS]
        members = list(Member.objects.filter(user__username__in=names).select_related("user"))
        instructor_ids = Instructor.objects.filter(is_removed=False).values_list(
            "user_id", flat=True
        )
        extras = (
            Member.objects.filter(is_removed=False)
            .exclude(user_id__in=instructor_ids)
            .exclude(user__username__in=names)
            .select_related("user")[:60]
        )
        seen = {str(member.id) for member in members}
        for member in extras:
            if str(member.id) not in seen:
                members.append(member)
                seen.add(str(member.id))
        return members

    def _templates(self, instructor, extra=True):
        names = [("Power Ride estándar", "Power Ride"), ("HIIT 45′", "HIIT")]
        if extra:
            names.append(("Friday party ride", "Party"))
        for name, fmt in names:
            PlaylistTemplate.objects.get_or_create(
                instructor=instructor,
                name=name,
                defaults={"class_format": fmt},
            )

    def _title_for(self, day: date, hour: int, base: str) -> str:
        if hour in (7, 8) and day.weekday() in (1, 3):
            return "Morning Climb"
        return base

    def _ensure_schedules(
        self, instructor, room, weekday_hours, weekend_hours, start_day, end_day, today
    ):
        existing = {
            timezone.localtime(start, SANTIAGO).replace(second=0, microsecond=0)
            for start in Schedule.objects.filter(instructor=instructor).values_list(
                "start_time", flat=True
            )
        }
        schedules = []
        day = start_day
        while day <= end_day:
            hours = weekday_hours if day.weekday() < 5 else weekend_hours
            for hour, base_title in hours:
                start_time = _aware(day, hour)
                if start_time in existing:
                    continue
                past = start_time.date() < today
                schedules.append(
                    Schedule(
                        title=self._title_for(day, hour, base_title),
                        description=DEMO_CLASS_DESCRIPTION,
                        instructor=instructor,
                        start_time=start_time,
                        duration_minutes=45,
                        room=room,
                        status=(
                            schedule_constants.SCHEDULE_STATUS_COMPLETED
                            if past
                            else schedule_constants.SCHEDULE_STATUS_SCHEDULED
                        ),
                    )
                )
                existing.add(start_time)
            day += timedelta(days=1)
        if schedules:
            Schedule.objects.bulk_create(schedules, batch_size=500)
        created_starts = [item.start_time for item in schedules]
        if not created_starts:
            return []
        return list(
            Schedule.objects.filter(
                instructor=instructor,
                description=DEMO_CLASS_DESCRIPTION,
                start_time__in=created_starts,
            )
        )

    def _fill(self, rng, room, members, schedules, today):
        first_timers = members[-FIRST_TIMER_COUNT:] if len(members) >= FIRST_TIMER_COUNT else []
        regulars = members[:-FIRST_TIMER_COUNT] if first_timers else list(members)
        reservations = []
        bike_count = min(room.capacity, 40)
        for index, schedule in enumerate(schedules):
            local_day = timezone.localtime(schedule.start_time, SANTIAGO).date()
            is_full = index % 17 == 0
            occupied = bike_count if is_full else int(ROSTER_SIZE * (0.85 + (index % 5) * 0.03))
            occupied = min(
                occupied,
                bike_count,
                len(members),
                ROSTER_SIZE if not is_full else bike_count,
            )
            occupied = max(8, occupied) if len(members) >= 8 else len(members)
            pool = list(regulars)
            if local_day >= today:
                pool = regulars + first_timers
            chosen = rng.sample(pool, k=min(occupied, len(pool)))
            spots = rng.sample(range(1, bike_count + 1), k=len(chosen))
            for member, spot in zip(chosen, spots):
                if local_day >= today:
                    status = member_constants.RESERVATION_STATUS_RESERVED
                elif rng.random() < 0.08:
                    status = member_constants.RESERVATION_STATUS_MISSED
                else:
                    status = member_constants.RESERVATION_STATUS_ATTENDED
                notes = ""
                roll = rng.random()
                if roll < 0.07:
                    notes = FUN_RIDER_NOTES[0]
                elif roll < 0.14:
                    notes = FUN_RIDER_NOTES[1]
                elif roll < 0.28:
                    notes = FUN_RIDER_NOTES[rng.randrange(2, len(FUN_RIDER_NOTES))]
                reservations.append(
                    Reservation(
                        member=member, schedule=schedule, status=status, spot=spot, notes=notes
                    )
                )
        Reservation.objects.bulk_create(reservations, batch_size=1000)

    def _playlist_spec(self, title: str):
        title = title or ""
        if any(token in title.upper() for token in ("HIIT", "NIGHT", "AFTER", "SCULPT")):
            return "HIIT 45′", HIIT_PLAYLIST_SEGMENTS
        return "Power Ride estándar", POWER_PLAYLIST_SEGMENTS

    def _backfill_playlists(self, instructor):
        missing = list(
            Schedule.objects.filter(instructor=instructor, is_removed=False)
            .filter(playlist__isnull=True)
            .order_by("start_time")
        )
        if not missing:
            return
        playlists = []
        for schedule in missing:
            title, spec = self._playlist_spec(schedule.title)
            playlists.append(
                ClassPlaylist(
                    schedule=schedule,
                    instructor=instructor,
                    title=title,
                    total_duration_minutes=45,
                )
            )
        ClassPlaylist.objects.bulk_create(playlists, batch_size=500)
        created = {
            item.schedule_id: item
            for item in ClassPlaylist.objects.filter(schedule_id__in=[row.id for row in missing])
        }
        segments = []
        tracks_by_key = {}
        for schedule in missing:
            playlist = created.get(schedule.id)
            if playlist is None:
                continue
            _, spec = self._playlist_spec(schedule.title)
            for order, (name, duration, bpm_range, tracks) in enumerate(spec):
                segments.append(
                    PlaylistSegment(
                        playlist=playlist,
                        name=name,
                        order=order,
                        duration_minutes=duration,
                        bpm_range=bpm_range,
                    )
                )
                tracks_by_key[(playlist.id, order)] = tracks
        PlaylistSegment.objects.bulk_create(segments, batch_size=500)
        persisted = PlaylistSegment.objects.filter(
            playlist_id__in=[item.id for item in created.values()]
        )
        tracks = []
        for segment in persisted:
            for track_order, (title, artist, bpm, seconds) in enumerate(
                tracks_by_key.get((segment.playlist_id, segment.order), ())
            ):
                tracks.append(
                    PlaylistTrack(
                        segment=segment,
                        title=title,
                        artist=artist,
                        bpm=bpm,
                        duration_seconds=seconds,
                        order=track_order,
                    )
                )
        if tracks:
            PlaylistTrack.objects.bulk_create(tracks, batch_size=1000)

    def _backfill_ratings(self, rng, instructor):
        past = Schedule.objects.filter(
            instructor=instructor,
            start_time__lt=timezone.now(),
        ).filter(class_rating__isnull=True)
        ratings = []
        for schedule in past:
            value = Decimal("4.6") + Decimal(str(rng.choice([0, 0.1, 0.2, 0.3, 0.4])))
            ratings.append(
                ClassRating(
                    schedule=schedule,
                    rating=min(value, Decimal("5.0")),
                    rating_count=rng.randint(8, 28),
                )
            )
        ClassRating.objects.bulk_create(ratings, batch_size=500)

    def _ensure_events(self, instructors, room, start_day, end_day, today):
        if not instructors:
            return 0
        kristina = next(
            (item for item in instructors if item.user.username == DEMO_SHOWCASE_USERNAME),
            instructors[0],
        )
        existing = {
            timezone.localtime(start, SANTIAGO).replace(second=0, microsecond=0)
            for start in Schedule.objects.filter(
                description__startswith=DEMO_EVENT_DESCRIPTION
            ).values_list("start_time", flat=True)
        }
        schedules = []
        year = start_day.year
        while year <= end_day.year:
            for month, day, title, hour, blurb in SPECIAL_EVENTS:
                try:
                    event_day = date(year, month, day)
                except ValueError:
                    continue
                if event_day < start_day or event_day > end_day:
                    continue
                start_time = _aware(event_day, hour)
                if start_time in existing:
                    continue
                instructor = (
                    kristina if month in (2, 7, 12) else instructors[month % len(instructors)]
                )
                past = event_day < today
                blurb_extra = FUN_CLASS_BLURBS[month % len(FUN_CLASS_BLURBS)]
                schedules.append(
                    Schedule(
                        title=title,
                        description=f"{DEMO_EVENT_DESCRIPTION}\n{blurb}\n{blurb_extra}",
                        instructor=instructor,
                        start_time=start_time,
                        duration_minutes=60,
                        room=room,
                        status=(
                            schedule_constants.SCHEDULE_STATUS_COMPLETED
                            if past
                            else schedule_constants.SCHEDULE_STATUS_SCHEDULED
                        ),
                    )
                )
                existing.add(start_time)
            year += 1
        if not schedules:
            return 0
        Schedule.objects.bulk_create(schedules, batch_size=200)
        created = list(
            Schedule.objects.filter(
                description__startswith=DEMO_EVENT_DESCRIPTION,
                start_time__in=[item.start_time for item in schedules],
            )
        )
        riders = self._riders()
        if created and riders:
            self._fill(Random("events"), room, riders, created, today)
        for instructor in {item.instructor for item in created}:
            self._backfill_playlists(instructor)
            self._backfill_ratings(Random(f"event:{instructor.user.username}"), instructor)
        return len(created)

    def _waitlists(self, rng, members, today):
        if not members:
            return
        upcoming = list(
            Schedule.objects.filter(
                description__startswith="demo.coach",
                start_time__date__gte=today,
            )
            .annotate(taken=Count("reservations"))
            .order_by("start_time")[:48]
        )
        already = set(
            WaitlistEntry.objects.filter(schedule__in=upcoming).values_list(
                "member_id", "schedule_id"
            )
        )
        reserved = {
            (str(member_id), str(schedule_id))
            for member_id, schedule_id in Reservation.objects.filter(
                schedule__in=upcoming
            ).values_list("member_id", "schedule_id")
        }
        rows = []
        for schedule in upcoming:
            if schedule.taken < 12:
                continue
            taken_members = {
                str(member_id) for member_id, sid in reserved if str(sid) == str(schedule.id)
            }
            pool = [
                member
                for member in members
                if str(member.id) not in taken_members and (member.id, schedule.id) not in already
            ]
            if not pool:
                continue
            for member in rng.sample(pool, k=min(3, len(pool))):
                rows.append(
                    WaitlistEntry(
                        member=member,
                        schedule=schedule,
                        status=member_constants.WAITLIST_STATUS_WAITING,
                    )
                )
                already.add((member.id, schedule.id))
        if rows:
            WaitlistEntry.objects.bulk_create(rows, batch_size=200)

    def _notifications(self, rng, members):
        if Notification.objects.filter(subject__startswith="[demo.coach]").exists():
            return
        subjects = (
            "[demo.coach] Kristina abrió un Girod Fest — hay glitter en el aire",
            "[demo.coach] Usain te retó a un sprint. El lightning pose es mandatory",
            "[demo.coach] Tu puesto favorito sobrevivió otro Valentine's Ride",
            "[demo.coach] Michelle Obama: when they go low, we climb high — mañana 9am",
        )
        rows = []
        for member in members[:20]:
            subject = subjects[rng.randrange(len(subjects))]
            rows.append(
                Notification(
                    user=member.user,
                    subject=subject,
                    message=(
                        f"Hola {member.user.first_name}: PulseFit te extraña en el clip-in. "
                        "Hay eventos hasta febrero y sí, el cool-down incluye drama."
                    ),
                    status=Notification.STATUS.sent,
                    transport=Notification.TRANSPORT.mail,
                )
            )
        Notification.objects.bulk_create(rows, batch_size=100)
