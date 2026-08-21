"""Seed a realistic PulseFit studio so the admin dashboard has charts to show.

Idempotent: demo rows are tagged with the `demo.dash.` username prefix.
Pass --reset to wipe previous demo rows and recreate them.
"""

from datetime import datetime, timedelta
from random import Random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
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
from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()

INSTRUCTORS = [
    ("Camila", "Rojas"),
    ("Diego", "Muñoz"),
    ("Valentina", "Soto"),
    ("Nicolás", "Paz"),
    ("Paz", "Leiva"),
]

PLANS = [
    ("Ilimitado", plan_constants.PLAN_TYPE_MEMBERSHIP, 89000, 30, None),
    ("Premium", plan_constants.PLAN_TYPE_MEMBERSHIP, 69000, 30, None),
    ("Smart 8", plan_constants.PLAN_TYPE_PACKAGE, 49000, 30, 8),
    ("Estudiante", plan_constants.PLAN_TYPE_MEMBERSHIP, 39000, 30, None),
    ("Drop-in", plan_constants.PLAN_TYPE_PACKAGE, 12000, 1, 1),
]

CLASS_HOURS = [6, 7, 9, 12, 18, 19, 20]
FORMAT_WEIGHTS = {
    "RIDE": 0.32,
    "POWER": 0.22,
    "YOGA": 0.14,
    "SCULPT": 0.16,
    "REFORMER": 0.16,
}


class Command(BaseCommand):
    help = "Create demo schedules, reservations and purchases for the admin dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete previous demo.dash.* rows before seeding.",
        )

    def handle(self, *args, **options):
        rng = Random(42)
        if options["reset"]:
            self._wipe()
            self.stdout.write(self.style.WARNING("Removed previous dashboard demo data."))

        if User.objects.filter(username__startswith=DEMO_USERNAME_PREFIX).exists():
            self.stdout.write(
                self.style.SUCCESS("Dashboard demo data already exists. Use --reset to recreate.")
            )
            return

        today = timezone.localdate()
        studio, room = self._studio()
        instructors = self._instructors()
        plans = self._plans()
        members = self._members(rng, plans, today)
        self._schedules_and_reservations(rng, instructors, room, members, today)
        self._recent_purchases(rng, members, plans, today)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded dashboard demo: {len(members)} socios, {len(instructors)} instructores, sala {room.name}."
            )
        )

    def _wipe(self):
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
        address, _ = Address.objects.get_or_create(address="Camino El Alba 12345, demo")
        studio, _ = Studio.objects.get_or_create(
            name="PulseFit Patio Andino (demo)",
            defaults={"address": address, "is_active": True},
        )
        room, _ = Room.objects.get_or_create(
            studio=studio,
            name="Sala Demo PulseFit",
            defaults={"capacity": 16, "is_active": True},
        )
        return studio, room

    def _instructors(self):
        instructors = []
        for first, last in INSTRUCTORS:
            slug = first.lower()
            user, created = User.objects.get_or_create(
                username=f"{DEMO_USERNAME_PREFIX}instructor.{slug}",
                defaults={
                    "email": f"instructor.{slug}@{DEMO_EMAIL_DOMAIN}",
                    "first_name": first,
                    "last_name": last,
                    "is_staff": True,
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
            instructor, _ = Instructor.objects.get_or_create(user=user)
            instructors.append(instructor)
        return instructors

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
        members = []
        mix = [plans[0]] * 18 + [plans[1]] * 12 + [plans[2]] * 8 + [plans[3]] * 4 + [plans[4]] * 6
        rng.shuffle(mix)
        first_names = [
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
        ]
        last_names = ["Silva", "Vargas", "Cortés", "Navarro", "Bravo", "Fuentes"]

        for index, plan in enumerate(mix, start=1):
            user, created = User.objects.get_or_create(
                username=f"{DEMO_USERNAME_PREFIX}member.{index:03d}",
                defaults={
                    "email": f"member.{index:03d}@{DEMO_EMAIL_DOMAIN}",
                    "first_name": first_names[(index - 1) % len(first_names)],
                    "last_name": last_names[(index - 1) % len(last_names)],
                },
            )
            if created:
                user.set_password("demo1234")
                user.save()
            member, _ = Member.objects.get_or_create(user=user)
            wallet, _ = Wallet.objects.get_or_create(user=user)
            activated = today - timedelta(days=rng.randint(5, 40))
            purchase = PlanPurchase.objects.create(
                user=user,
                plan=plan,
                price_paid=plan.price,
                activated_since=activated,
            )
            PlanPurchase.objects.filter(pk=purchase.pk).update(
                created=timezone.make_aware(datetime.combine(activated, datetime.min.time()))
            )
            wallet.active_membership_end_date = today + timedelta(days=rng.randint(5, 25))
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
            members.append(member)
        return members

    def _pick_format(self, rng):
        roll = rng.random()
        acc = 0
        for fmt, weight in FORMAT_WEIGHTS.items():
            acc += weight
            if roll <= acc:
                return fmt
        return CLASS_FORMATS[0]

    def _schedules_and_reservations(self, rng, instructors, room, members, today):
        schedules = []
        start_day = today - timedelta(days=89)
        for offset in range(90):
            day = start_day + timedelta(days=offset)
            hours = CLASS_HOURS if day.weekday() < 5 else [9, 10, 18, 19]
            for hour in hours:
                fmt = self._pick_format(rng)
                instructor = instructors[rng.randrange(len(instructors))]
                start_time = timezone.make_aware(datetime(day.year, day.month, day.day, hour, 0))
                status = schedule_constants.SCHEDULE_STATUS_SCHEDULED
                if day < today:
                    status = schedule_constants.SCHEDULE_STATUS_COMPLETED
                schedules.append(
                    Schedule(
                        title=f"{fmt} 45",
                        description="Clase demo dashboard",
                        instructor=instructor,
                        start_time=start_time,
                        duration_minutes=45,
                        room=room,
                        status=status,
                    )
                )
        Schedule.objects.bulk_create(schedules)
        created = list(
            Schedule.objects.filter(description="Clase demo dashboard").order_by("start_time")
        )

        reservations = []
        for schedule in created:
            hour = timezone.localtime(schedule.start_time).hour
            base = 0.78
            if hour in (7, 18, 19):
                base = 0.92
            elif hour in (6, 9, 20):
                base = 0.84
            occupied = max(
                8, min(room.capacity, int(room.capacity * (base + rng.uniform(-0.08, 0.08))))
            )
            chosen = rng.sample(members, k=occupied)
            for member in chosen:
                status = member_constants.RESERVATION_STATUS_ATTENDED
                if schedule.start_time.date() >= today:
                    status = member_constants.RESERVATION_STATUS_RESERVED
                elif rng.random() < 0.09:
                    status = member_constants.RESERVATION_STATUS_MISSED
                reservations.append(Reservation(member=member, schedule=schedule, status=status))
        Reservation.objects.bulk_create(reservations, batch_size=500)

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
