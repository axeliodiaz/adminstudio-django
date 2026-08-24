"""Seed a realistic PulseFit studio so dashboards have charts to show.

Idempotent: demo rows are tagged with the `demo.dash.` username prefix.
Pass --reset to wipe previous demo rows and recreate them.

Schedules cover last January through February of next year so the
admin dashboard and member "Mis estadísticas" page have past and upcoming
classes. Running the command again fills any missing days without duplicating
rows, backfills bike spots, and attaches a distinct ride history to every
active user (socios, staff and superusers).
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from random import Random

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from apps.analytics.constants import (
    CLASS_FORMATS,
    DEMO_EMAIL_DOMAIN,
    DEMO_PLAN_PREFIX,
    DEMO_USERNAME_PREFIX,
)
from apps.instructors.models import Instructor
from apps.members import constants as member_constants
from apps.members.models import Member, Reservation
from apps.plans import constants as plan_constants
from apps.plans.models import Plan
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.studios.models import Address, Room, Studio
from apps.users.demo_catalog import (
    DEMO_CLOSING,
    DEMO_OPENING,
    INSTRUCTORS as CELEBRITY_COACHES,
    MEMBERS as CELEBRITY_MEMBERS,
    demo_history_start as catalog_history_start,
    demo_horizon_end as catalog_horizon_end,
)
from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()

PLANS = [
    ("Ilimitado", plan_constants.PLAN_TYPE_MEMBERSHIP, 89000, 30, None),
    ("Premium", plan_constants.PLAN_TYPE_MEMBERSHIP, 69000, 30, None),
    ("Smart 8", plan_constants.PLAN_TYPE_PACKAGE, 49000, 30, 8),
    ("Estudiante", plan_constants.PLAN_TYPE_MEMBERSHIP, 39000, 30, None),
    ("Drop-in", plan_constants.PLAN_TYPE_PACKAGE, 12000, 1, 1),
]

CLASS_HOURS = [7, 12, 19]
FORMAT_WEIGHTS = {
    "RIDE": 0.32,
    "POWER": 0.22,
    "YOGA": 0.14,
    "SCULPT": 0.16,
    "REFORMER": 0.16,
}
DEMO_CLASS_DESCRIPTION = "Clase demo dashboard"
DEMO_RIDER_USERNAME = "chayanne"
DEMO_RESERVATION_NOTE = "demo.member-stats"
STORY_SPOTS = (7, 7, 7, 8, 4)
CLASSES_PER_WEEK = 3
DEMO_ROOM_CAPACITY = 48
STUDIO_BIKE_COUNT = 16
MIN_ATTENDED_FOR_STATS = 8
PERSONA_HOUR_SETS = (
    (7, 12),
    (12, 19),
    (7, 19),
    (7,),
    (19,),
    (12,),
)


def demo_horizon_end(today: date) -> date:
    """Cover remaining season through February of next year."""
    return catalog_horizon_end(today)


def demo_history_start(today: date) -> date:
    """1 January of last year."""
    return catalog_history_start(today)


def _iso_week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


class Command(BaseCommand):
    help = (
        "Create demo schedules, reservations and purchases through February of next year "
        "for the admin dashboard and per-user statistics."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previous demo.dash.* rows before seeding.",
        )
        parser.add_argument(
            "--until",
            help="Last calendar day to seed (YYYY-MM-DD). Defaults to end of February next year.",
        )
        parser.add_argument(
            "--history-days",
            type=int,
            help="How many days of history to include (default: 1 January of last year).",
        )
        parser.add_argument(
            "--as-of",
            help="Pretend today is this date (YYYY-MM-DD). Defaults to the local date.",
        )

    def handle(self, *args, **options):
        rng = Random(42)
        if options["reset"]:
            self._wipe()
            self.stdout.write(self.style.WARNING("Removed previous dashboard demo data."))
        call_command("seed_demo_catalog", verbosity=options["verbosity"])

        today = date.fromisoformat(options["as_of"]) if options["as_of"] else timezone.localdate()
        end_day = (
            date.fromisoformat(options["until"]) if options["until"] else demo_horizon_end(today)
        )
        if options["history_days"]:
            start_day = today - timedelta(days=max(1, options["history_days"]) - 1)
        else:
            start_day = demo_history_start(today)
        if start_day > end_day:
            start_day = end_day

        studio, room = self._studio()
        instructors = self._instructors()
        plans = self._plans()
        members = self._members(rng, plans, today)
        new_schedules = self._ensure_schedules(rng, instructors, room, start_day, end_day, today)
        if new_schedules:
            self._fill_occupancy(rng, room, members, new_schedules, today)
        self._backfill_spots(room)
        if not PlanPurchase.objects.filter(
            user__username__startswith=DEMO_USERNAME_PREFIX
        ).exists():
            self._recent_purchases(rng, members, plans, today)

        rider = self._showcase_rider(plans, today)
        stats_members = self._ensure_stats_members(plans, today, extra=(rider, *members))
        attached = self._attach_rider_stories(room, stats_members, today)
        schedules = Schedule.objects.filter(description=DEMO_CLASS_DESCRIPTION).count()
        last = (
            Schedule.objects.filter(description=DEMO_CLASS_DESCRIPTION)
            .order_by("-start_time")
            .values_list("start_time", flat=True)
            .first()
        )
        last_label = timezone.localtime(last).date().isoformat() if last else "—"
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded dashboard demo through {last_label}: {len(members)} socios demo, "
                f"{schedules} clases, {attached} reservas de historia de socio "
                f"(incluye {DEMO_RIDER_USERNAME})."
            )
        )

    def _wipe(self):
        Reservation.objects.filter(notes=DEMO_RESERVATION_NOTE).delete()
        demo_users = User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX)
        Reservation.objects.filter(member__user__in=demo_users).delete()
        Schedule.objects.filter(instructor__user__in=demo_users).delete()
        PlanPurchase.objects.filter(user__in=demo_users).delete()
        Plan.objects.filter(name__startswith=DEMO_PLAN_PREFIX).delete()
        Room.objects.filter(name="Sala Demo PulseFit").delete()
        Studio.objects.filter(name="PulseFit Patio Andino (demo)").delete()
        Address.objects.filter(address="Camino El Alba 12345, demo").delete()
        demo_users.delete()

    def _studio(self):
        address, _ = Address.objects.get_or_create(
            address="Camino El Alba 12345, demo",
            defaults={"latitude": "-33.402890", "longitude": "-70.580210"},
        )
        if address.latitude is None:
            address.latitude = "-33.402890"
            address.longitude = "-70.580210"
            address.save(update_fields=["latitude", "longitude"])
        studio, _ = Studio.objects.get_or_create(
            name="PulseFit Patio Andino (demo)",
            defaults={
                "address": address,
                "is_active": True,
                "opening_time": DEMO_OPENING,
                "closing_time": DEMO_CLOSING,
            },
        )
        studio.address = address
        studio.is_active = True
        studio.opening_time = DEMO_OPENING
        studio.closing_time = DEMO_CLOSING
        studio.save()
        room, _ = Room.objects.get_or_create(
            studio=studio,
            name="Sala Demo PulseFit",
            defaults={"capacity": DEMO_ROOM_CAPACITY, "is_active": True},
        )
        room.is_active = True
        if room.capacity < DEMO_ROOM_CAPACITY:
            room.capacity = DEMO_ROOM_CAPACITY
        room.save()
        return studio, room

    def _instructors(self):
        names = [persona.username for persona in CELEBRITY_COACHES]
        instructors = list(
            Instructor.objects.filter(user__username__in=names).select_related("user")
        )
        return instructors or list(Instructor.objects.filter(is_removed=False)[:8])

    def _plans(self):
        plans = []
        for name, plan_type, price, days, classes in PLANS:
            plan, _ = Plan.objects.get_or_create(
                name=f"{DEMO_PLAN_PREFIX}{name}",
                defaults={
                    "type": plan_type,
                    "price": price,
                    "duration_days": days,
                    "classes_included": classes,
                    "is_active": True,
                    "is_popular": name == "Ilimitado",
                },
            )
            plans.append(plan)
        return plans

    def _members(self, rng, plans, today):
        names = [persona.username for persona in CELEBRITY_MEMBERS]
        members = list(Member.objects.filter(user__username__in=names).select_related("user"))
        for index, member in enumerate(members, start=1):
            plan = plans[index % len(plans)]
            self._activate_wallet(member.user, plan, today, rng, index)
        return members

    def _activate_wallet(self, user, plan, today, rng, index):
        wallet, _ = Wallet.objects.get_or_create(user=user)
        if not PlanPurchase.objects.filter(user=user, plan=plan).exists():
            activated = today - timedelta(days=rng.randint(5, 40))
            purchase = PlanPurchase.objects.create(
                user=user,
                plan=plan,
                price_paid=plan.price,
                payment_method=plan_constants.PAYMENT_METHOD_WEBPAY,
                activated_since=activated,
            )
            PlanPurchase.objects.filter(pk=purchase.pk).update(
                created=timezone.make_aware(datetime.combine(activated, datetime.min.time()))
            )
        wallet.active_membership_end_date = today + timedelta(days=rng.randint(70, 110))
        wallet.is_unlimited_membership_active = "Ilimitado" in plan.name
        wallet.class_credits = (
            0 if wallet.is_unlimited_membership_active else (plan.classes_included or 12)
        )
        wallet.guest_pass_credits = (
            2 if "Premium" in plan.name or "Ilimitado" in plan.name else rng.randint(0, 1)
        )
        wallet.is_priority_booker = "Ilimitado" in plan.name or (
            "Premium" in plan.name and index % 2 == 0
        )
        wallet.can_freeze_membership = "Ilimitado" in plan.name
        wallet.save()

    def _showcase_rider(self, plans, today):
        smart = next((plan for plan in plans if "Smart 8" in plan.name), plans[2])
        user = User.objects.filter(username=DEMO_RIDER_USERNAME).first()
        if user is None:
            user = User.objects.create_user(
                username=DEMO_RIDER_USERNAME,
                email=f"chayanne@{DEMO_EMAIL_DOMAIN}",
                password="demo1234",
                first_name="Chayanne",
                last_name="Figueroa",
            )
        member, _ = Member.objects.get_or_create(user=user)
        wallet, _ = Wallet.objects.get_or_create(user=user)
        if not PlanPurchase.objects.filter(user=user, plan=smart).exists():
            PlanPurchase.objects.create(
                user=user,
                plan=smart,
                price_paid=smart.price,
                payment_method=plan_constants.PAYMENT_METHOD_MERCADOPAGO,
                activated_since=today - timedelta(days=20),
            )
        wallet.active_membership_end_date = catalog_horizon_end(today)
        wallet.is_unlimited_membership_active = False
        wallet.class_credits = 5
        wallet.guest_pass_credits = 2
        wallet.save()
        return member

    def _ensure_stats_members(self, plans, today, extra=()):
        """Every active user gets a Member profile plus a plan, so stats can render."""
        default_plan = next((plan for plan in plans if "Smart 8" in plan.name), plans[0])
        by_id = {}
        for member in extra:
            if member is not None:
                by_id[str(member.id)] = member

        for user in User.objects.filter(is_removed=False, is_active=True).order_by("username"):
            member, _ = Member.objects.get_or_create(user=user)
            member.user = user
            by_id[str(member.id)] = member
            if PlanPurchase.objects.filter(user=user).exists():
                continue
            rng = Random(f"wallet:{user.username}")
            plan = default_plan if user.is_staff else plans[rng.randrange(len(plans))]
            self._activate_wallet(user, plan, today, rng, rng.randint(1, 40))

        return list(by_id.values())

    def _pick_format(self, rng):
        roll = rng.random()
        acc = 0
        for fmt, weight in FORMAT_WEIGHTS.items():
            acc += weight
            if roll <= acc:
                return fmt
        return CLASS_FORMATS[0]

    def _ensure_schedules(self, rng, instructors, room, start_day, end_day, today):
        existing = {
            timezone.localtime(start).replace(minute=0, second=0, microsecond=0)
            for start in Schedule.objects.filter(
                room=room, description=DEMO_CLASS_DESCRIPTION
            ).values_list("start_time", flat=True)
        }
        schedules = []
        total_days = (end_day - start_day).days + 1
        for offset in range(total_days):
            day = start_day + timedelta(days=offset)
            hours = CLASS_HOURS if day.weekday() < 5 else [10, 18]
            for hour in hours:
                start_time = timezone.make_aware(datetime(day.year, day.month, day.day, hour, 0))
                if start_time in existing:
                    continue
                fmt = self._pick_format(rng)
                instructor = instructors[rng.randrange(len(instructors))]
                status = schedule_constants.SCHEDULE_STATUS_SCHEDULED
                if day < today:
                    status = schedule_constants.SCHEDULE_STATUS_COMPLETED
                schedules.append(
                    Schedule(
                        title=f"{fmt} 45",
                        description=DEMO_CLASS_DESCRIPTION,
                        instructor=instructor,
                        start_time=start_time,
                        duration_minutes=45,
                        room=room,
                        status=status,
                    )
                )
        if schedules:
            Schedule.objects.bulk_create(schedules, batch_size=500)
        created_starts = {item.start_time for item in schedules}
        if not created_starts:
            return []
        return list(
            Schedule.objects.filter(
                description=DEMO_CLASS_DESCRIPTION, start_time__in=created_starts
            )
        )

    def _fill_occupancy(self, rng, room, members, schedules, today):
        if not members:
            return
        reservations = []
        for schedule in schedules:
            hour = timezone.localtime(schedule.start_time).hour
            base = 0.78
            if hour in (7, 18, 19):
                base = 0.92
            elif hour in (6, 9, 20):
                base = 0.84
            occupied = max(
                8,
                min(STUDIO_BIKE_COUNT, int(STUDIO_BIKE_COUNT * (base + rng.uniform(-0.08, 0.08)))),
            )
            occupied = min(occupied, len(members), room.capacity, STUDIO_BIKE_COUNT)
            chosen = rng.sample(members, k=occupied)
            spots = rng.sample(range(1, STUDIO_BIKE_COUNT + 1), k=occupied)
            local_day = timezone.localtime(schedule.start_time).date()
            for member, spot in zip(chosen, spots):
                status = member_constants.RESERVATION_STATUS_ATTENDED
                if local_day >= today:
                    status = member_constants.RESERVATION_STATUS_RESERVED
                elif rng.random() < 0.09:
                    status = member_constants.RESERVATION_STATUS_MISSED
                reservations.append(
                    Reservation(
                        member=member,
                        schedule=schedule,
                        status=status,
                        spot=spot,
                    )
                )
        Reservation.objects.bulk_create(reservations, batch_size=500)

    def _backfill_spots(self, room):
        taken_by_schedule = defaultdict(set)
        open_by_schedule = defaultdict(list)
        qs = Reservation.objects.filter(schedule__room=room).only("id", "schedule_id", "spot")
        for reservation in qs.iterator():
            if reservation.spot:
                taken_by_schedule[reservation.schedule_id].add(reservation.spot)
            else:
                open_by_schedule[reservation.schedule_id].append(reservation)
        if not open_by_schedule:
            return
        updates = []
        for schedule_id, rows in open_by_schedule.items():
            taken = taken_by_schedule[schedule_id]
            available = [spot for spot in range(1, room.capacity + 1) if spot not in taken]
            for reservation, spot in zip(rows, available):
                reservation.spot = spot
                updates.append(reservation)
        if updates:
            Reservation.objects.bulk_update(updates, ["spot"], batch_size=500)

    def _attach_rider_stories(self, room, members, today):
        members = [member for member in members if member is not None]
        if not members:
            return 0
        schedules = list(
            Schedule.objects.filter(description=DEMO_CLASS_DESCRIPTION, room=room)
            .select_related("instructor__user")
            .order_by("start_time")
        )
        if not schedules:
            return 0

        occupancy = {
            str(row["schedule_id"]): row["total"]
            for row in (
                Reservation.objects.filter(schedule__in=schedules)
                .exclude(status=member_constants.RESERVATION_STATUS_CANCELLED)
                .values("schedule_id")
                .annotate(total=Count("id"))
            )
        }
        spots_taken = defaultdict(set)
        already = defaultdict(set)
        attended_by_member = defaultdict(int)
        for schedule_id, member_id, spot, status in Reservation.objects.filter(
            schedule__in=schedules
        ).values_list("schedule_id", "member_id", "spot", "status"):
            already[str(schedule_id)].add(str(member_id))
            if spot:
                spots_taken[str(schedule_id)].add(spot)
            if status == member_constants.RESERVATION_STATUS_ATTENDED:
                attended_by_member[str(member_id)] += 1

        instructors = []
        seen_instructors = set()
        for schedule in schedules:
            instructor = schedule.instructor
            if instructor is None or str(instructor.id) in seen_instructors:
                continue
            seen_instructors.add(str(instructor.id))
            instructors.append(instructor)

        to_create = []
        for member in members:
            persona = self._member_persona(member, instructors)
            to_create.extend(
                self._story_reservations(
                    member,
                    schedules,
                    today,
                    room.capacity,
                    occupancy,
                    spots_taken,
                    already,
                    persona,
                    attended=attended_by_member[str(member.id)],
                )
            )
        if to_create:
            Reservation.objects.bulk_create(to_create, batch_size=500)
        return len(to_create)

    def _member_persona(self, member, instructors):
        rng = Random(f"stats:{member.user.username}")
        favorite = instructors[rng.randrange(len(instructors))] if instructors else None
        return {
            "hours": PERSONA_HOUR_SETS[rng.randrange(len(PERSONA_HOUR_SETS))],
            "favorite_id": favorite.id if favorite else None,
            "classes_per_week": rng.choice((2, 3, 4)),
            "spots": tuple(rng.sample(range(1, 17), k=5)),
            "prefer_power": rng.random() < 0.45,
            "prefer_ride": rng.random() < 0.55,
            "miss_every": rng.choice((0, 9, 11, 13)),
        }

    def _story_reservations(
        self,
        member,
        schedules,
        today,
        capacity,
        occupancy,
        spots_taken,
        already,
        persona,
        attended=0,
    ):
        scored = sorted(
            schedules, key=lambda item: (-self._story_score(item, persona), item.start_time)
        )
        used_days = set()
        per_week = defaultdict(int)
        member_key = str(member.id)
        weekly_cap = persona.get("classes_per_week") or CLASSES_PER_WEEK
        miss_every = persona.get("miss_every") or 0
        preferred_spots = persona.get("spots") or STORY_SPOTS
        for schedule in schedules:
            if member_key not in already[str(schedule.id)]:
                continue
            local_day = timezone.localtime(schedule.start_time).date()
            used_days.add(local_day)
            per_week[_iso_week_start(local_day)] += 1
        picked = []
        for schedule in scored:
            local_dt = timezone.localtime(schedule.start_time)
            local_day = local_dt.date()
            week = _iso_week_start(local_day)
            sid = str(schedule.id)
            needs_floor = (
                attended
                + sum(
                    1
                    for _schedule, status, _spot in picked
                    if status == member_constants.RESERVATION_STATUS_ATTENDED
                )
                < MIN_ATTENDED_FOR_STATS
            )
            if str(member.id) in already[sid]:
                continue
            if occupancy.get(sid, 0) >= capacity:
                continue
            if local_day in used_days:
                continue
            if not needs_floor and per_week[week] >= weekly_cap:
                continue
            free_spot = self._next_spot(spots_taken[sid], capacity, preferred_spots)
            if free_spot is None:
                continue
            status = member_constants.RESERVATION_STATUS_RESERVED
            if local_day < today:
                miss = miss_every and ((len(picked) + 1) % miss_every == 0)
                status = (
                    member_constants.RESERVATION_STATUS_MISSED
                    if miss
                    else member_constants.RESERVATION_STATUS_ATTENDED
                )
            picked.append((schedule, status, free_spot))
            used_days.add(local_day)
            per_week[week] += 1
            occupancy[sid] = occupancy.get(sid, 0) + 1
            spots_taken[sid].add(free_spot)
            already[sid].add(str(member.id))

        return [
            Reservation(
                member=member,
                schedule=schedule,
                status=status,
                spot=spot,
                notes=DEMO_RESERVATION_NOTE,
            )
            for schedule, status, spot in picked
        ]

    def _story_score(self, schedule, persona) -> int:
        hour = timezone.localtime(schedule.start_time).hour
        title = schedule.title or ""
        score = 0
        preferred_hours = persona.get("hours") or (18, 19)
        if hour in preferred_hours:
            score += 6
        elif hour in (7, 12, 19):
            score += 1
        if persona.get("favorite_id") and schedule.instructor_id == persona["favorite_id"]:
            score += 5
        if persona.get("prefer_power") and "POWER" in title:
            score += 3
        elif persona.get("prefer_ride") and "RIDE" in title:
            score += 3
        elif "POWER" in title or "RIDE" in title:
            score += 1
        return score

    def _next_spot(self, taken, capacity, preferred=STORY_SPOTS):
        for spot in preferred:
            if spot not in taken and spot <= capacity:
                return spot
        for spot in range(1, capacity + 1):
            if spot not in taken:
                return spot
        return None

    def _recent_purchases(self, rng, members, plans, today):
        paid_plans = [plan for plan in plans if "Drop-in" not in plan.name]
        target = 4_800_000
        spent = 0
        index = 0
        while spent < target and index < 80:
            member = members[index % len(members)]
            plan = rng.choice(paid_plans)
            day = today - timedelta(days=rng.randint(0, 89))
            purchase = PlanPurchase.objects.create(
                user=member.user,
                plan=plan,
                price_paid=plan.price,
                activated_since=day,
            )
            PlanPurchase.objects.filter(pk=purchase.pk).update(
                created=timezone.make_aware(datetime.combine(day, datetime.min.time()))
                + timedelta(hours=rng.randint(9, 20))
            )
            spent += plan.price
            index += 1
