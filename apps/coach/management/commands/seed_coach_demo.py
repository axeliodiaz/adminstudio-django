"""Seed PulseFit coach demo data (Tomás + Axelio class calendar).

Idempotent. Demo rows are tagged with `demo.coach` in Schedule.description
and `demo.coach.*` usernames. Showcase coach is `tomasride`.
`--reset` only removes demo.coach.* users, tomasride, and schedules marked
demo.coach (plus related reservations/playlists/ratings). Axelio is never deleted.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from random import Random
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.coach.constants import (
    DEMO_CLASS_DESCRIPTION,
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
from apps.members.models import Member, Reservation
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.studios.models import Address, Room, Studio

User = get_user_model()
SANTIAGO = ZoneInfo("America/Santiago")
SEED_START = date(2026, 1, 1)
SEED_END = date(2026, 10, 31)
RIDER_COUNT = 40
FIRST_TIMER_COUNT = 4

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

FIRST_NAMES = [
    "Ana",
    "Benja",
    "Carla",
    "Dani",
    "Elena",
    "Felipe",
    "Gabi",
    "Hugo",
    "Inés",
    "Javiera",
    "Karla",
    "Lucas",
    "Maca",
    "Nico",
    "Olga",
    "Pablo",
    "Quena",
    "Rafa",
    "Sofía",
    "Tomás",
]
LAST_NAMES = ["Silva", "Vargas", "Cortés", "Navarro", "Bravo", "Fuentes", "Leiva", "Paz"]


def _aware(day: date, hour: int, minute: int = 0) -> datetime:
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SANTIAGO)


class Command(BaseCommand):
    help = "Create PulseFit coach demo data (Tomás + Axelio) from Jan–Oct 2026."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previous demo.coach rows (not Axelio) before seeding.",
        )

    def handle(self, *args, **options):
        rng = Random(7)
        if options["reset"]:
            self._wipe()
            self.stdout.write(self.style.WARNING("Removed previous coach demo data."))

        room = self._room()
        tomas = self._tomas()
        axelio, axelio_created = self._axelio()
        riders = self._riders()
        self._templates(tomas)
        self._templates(axelio, extra=False)

        for instructor, hours in (
            (tomas, ((7, "Power Ride"), (19, "HIIT Ride"))),
            (axelio, ((8, "Power Ride"), (18, "HIIT Ride"))),
        ):
            new_schedules = self._ensure_schedules(instructor, room, hours)
            if new_schedules:
                self._fill(rng, room, riders, new_schedules)

        self._backfill_playlists(tomas)
        self._backfill_ratings(rng, tomas)
        self._backfill_ratings(rng, axelio)

        self.stdout.write(self.style.SUCCESS(f"Login: {DEMO_SHOWCASE_USERNAME} / coach1234"))
        self.stdout.write(self.style.SUCCESS("Coach axelio linked (is_coach=true)"))
        if axelio_created:
            self.stdout.write(
                self.style.NOTICE("Created user axelio (password left as set on create).")
            )

    def _wipe(self):
        demo_schedules = Schedule.objects.filter(description=DEMO_CLASS_DESCRIPTION)
        ClassRating.objects.filter(schedule__in=demo_schedules).delete()
        ClassPlaylist.objects.filter(schedule__in=demo_schedules).delete()
        Reservation.objects.filter(schedule__in=demo_schedules).delete()
        demo_schedules.delete()

        demo_users = User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
        showcase = User.objects.filter(username=DEMO_SHOWCASE_USERNAME)
        wipe_users = demo_users | showcase
        PlaylistTemplate.objects.filter(instructor__user__in=wipe_users).delete()
        Reservation.objects.filter(member__user__in=wipe_users).delete()
        Instructor.objects.filter(user__in=wipe_users).delete()
        Member.objects.filter(user__in=wipe_users).delete()
        wipe_users.delete()

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

    def _tomas(self):
        user, created = User.objects.get_or_create(
            username=DEMO_SHOWCASE_USERNAME,
            defaults={
                "email": "tomas.munoz@pulsefit.cl",
                "first_name": "Tomás",
                "last_name": "Muñoz",
                "phone_number": "+56911112222",
            },
        )
        if created:
            user.set_password("coach1234")
            user.save()
        instructor, _ = Instructor.objects.get_or_create(user=user)
        instructor.tagline = "Power Ride · HIIT cycling"
        instructor.description = "Coach de indoor cycling en PulseFit. Power, climbs y sprints."
        instructor.instagram_username = "tomasride"
        instructor.instructor_since = date(2022, 1, 15)
        instructor.specialties = ["Power Ride", "HIIT", "Climb"]
        instructor.languages = ["Español", "English"]
        instructor.certifications = ["Schwinn Indoor Cycling", "First Aid / RCP"]
        instructor.save()
        return instructor

    def _axelio(self):
        user = User.objects.filter(username="axelio").first()
        if user is None:
            user = User.objects.filter(email="diaz.axelio@gmail.com").first()
        created = False
        if user is None:
            user = User.objects.create_user(
                username="axelio",
                email="diaz.axelio@gmail.com",
                first_name="Axel",
                last_name="Diaz",
                password="coach1234",
            )
            created = True
        instructor, _ = Instructor.objects.get_or_create(user=user)
        instructor.tagline = "Indoor cycling · PulseFit"
        instructor.specialties = ["Power Ride", "HIIT"]
        instructor.languages = ["Español", "English"]
        if not instructor.instructor_since:
            instructor.instructor_since = date(2022, 1, 15)
        instructor.save()
        return instructor, created

    def _riders(self):
        members = []
        for index in range(1, RIDER_COUNT + 1):
            username = f"{DEMO_USERNAME_PREFIX}rider{index:02d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"rider{index:02d}@pulsefit.cl",
                    "first_name": FIRST_NAMES[(index - 1) % len(FIRST_NAMES)],
                    "last_name": LAST_NAMES[(index - 1) % len(LAST_NAMES)],
                },
            )
            if created:
                user.set_password("rider1234")
                is_first_timer = index > RIDER_COUNT - FIRST_TIMER_COUNT
                if not is_first_timer:
                    user.seat_height = 70 + (index % 12)
                    user.seat_distance = 8 + (index % 6)
                    user.handlebar_distance = 10 + (index % 5)
                    user.cycling_shoe_size = Decimal("40.0") + (index % 6) * Decimal("0.5")
                user.save()
            member, _ = Member.objects.get_or_create(user=user)
            members.append(member)
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

    def _ensure_schedules(self, instructor, room, hour_titles):
        existing = {
            timezone.localtime(start, SANTIAGO).replace(second=0, microsecond=0)
            for start in Schedule.objects.filter(
                instructor=instructor, description=DEMO_CLASS_DESCRIPTION
            ).values_list("start_time", flat=True)
        }
        schedules = []
        day = SEED_START
        while day <= SEED_END:
            if day.weekday() < 5:
                for hour, base_title in hour_titles:
                    start_time = _aware(day, hour)
                    if start_time in existing:
                        continue
                    past = start_time.date() < timezone.now().astimezone(SANTIAGO).date()
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

    def _fill(self, rng, room, members, schedules):
        first_timers = members[-FIRST_TIMER_COUNT:]
        regulars = members[:-FIRST_TIMER_COUNT]
        today = timezone.now().astimezone(SANTIAGO).date()
        reservations = []
        for index, schedule in enumerate(schedules):
            local_day = timezone.localtime(schedule.start_time, SANTIAGO).date()
            is_full = index % 17 == 0
            occupied = (
                room.capacity if is_full else int(room.capacity * (0.72 + (index % 5) * 0.05))
            )
            occupied = min(occupied, room.capacity, len(members))
            pool = list(regulars)
            if local_day >= today:
                pool = regulars + first_timers
            chosen = rng.sample(pool, k=min(occupied, len(pool)))
            spots = rng.sample(range(1, room.capacity + 1), k=len(chosen))
            for member, spot in zip(chosen, spots):
                if local_day >= today:
                    status = member_constants.RESERVATION_STATUS_RESERVED
                elif rng.random() < 0.08:
                    status = member_constants.RESERVATION_STATUS_MISSED
                else:
                    status = member_constants.RESERVATION_STATUS_ATTENDED
                notes = ""
                if rng.random() < 0.06:
                    notes = "Lesión de rodilla — evitar sprints largos."
                elif rng.random() < 0.08:
                    notes = "Prefiere handlebar más cerca. Coach: revisar setup."
                reservations.append(
                    Reservation(
                        member=member, schedule=schedule, status=status, spot=spot, notes=notes
                    )
                )
        Reservation.objects.bulk_create(reservations, batch_size=1000)

    def _backfill_playlists(self, instructor):
        if ClassPlaylist.objects.filter(instructor=instructor, is_removed=False).exists():
            return
        sample = list(
            Schedule.objects.filter(
                instructor=instructor, description=DEMO_CLASS_DESCRIPTION, title__icontains="Power"
            ).order_by("start_time")[:12]
        )
        for schedule in sample:
            playlist = ClassPlaylist.objects.create(
                schedule=schedule,
                instructor=instructor,
                title="Power Ride estándar",
                total_duration_minutes=45,
            )
            for order, (name, duration, bpm_range, tracks) in enumerate(POWER_PLAYLIST_SEGMENTS):
                segment = PlaylistSegment.objects.create(
                    playlist=playlist,
                    name=name,
                    order=order,
                    duration_minutes=duration,
                    bpm_range=bpm_range,
                )
                for track_order, (title, artist, bpm, seconds) in enumerate(tracks):
                    PlaylistTrack.objects.create(
                        segment=segment,
                        title=title,
                        artist=artist,
                        bpm=bpm,
                        duration_seconds=seconds,
                        order=track_order,
                    )

    def _backfill_ratings(self, rng, instructor):
        past = Schedule.objects.filter(
            instructor=instructor,
            description=DEMO_CLASS_DESCRIPTION,
            start_time__lt=timezone.now(),
        ).exclude(class_rating__isnull=False)
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
