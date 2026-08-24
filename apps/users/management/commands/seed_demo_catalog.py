"""Seed studios, celebrity users, instructors, members, plans and promos."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.instructors.models import Instructor
from apps.members.models import Member
from apps.plans import constants as plan_constants
from apps.plans.models import Benefit, Plan, PromoCode
from apps.studios.models import Address, Room, Studio
from apps.users.demo_catalog import (
    DEMO_CLOSING,
    DEMO_OPENING,
    DEMO_PASSWORD,
    DEMO_STUDIO_ADDRESS,
    DEMO_STUDIO_LAT,
    DEMO_STUDIO_LNG,
    INSTRUCTORS,
    MEMBERS,
    PROMO_CODES,
    apply_persona_instructor,
    apply_persona_user,
    is_preserved_username,
    persona_user_defaults,
)
from apps.wallets.models import PlanPurchase, Wallet

User = get_user_model()

PLANS = [
    ("Ilimitado Glitter", plan_constants.PLAN_TYPE_MEMBERSHIP, 89000, 30, None, 2, True, True),
    ("Premium Oscar", plan_constants.PLAN_TYPE_MEMBERSHIP, 69000, 30, None, 1, False, False),
    ("Smart 8 Sprints", plan_constants.PLAN_TYPE_PACKAGE, 49000, 30, 8, 0, False, False),
    ("Estudiante Remix", plan_constants.PLAN_TYPE_MEMBERSHIP, 39000, 30, None, 0, False, False),
    ("Drop-in Cameo", plan_constants.PLAN_TYPE_PACKAGE, 12000, 1, 1, 0, False, False),
]

BENEFITS = [
    ("Toalla olímpica con monograma", "Bordada con tu nombre de famoseo indoor."),
    ("Café de especialidad post-ride", "Espresso de premio, no de máquina triste."),
    ("Priority booking VIP", "Reservas 24h antes que el resto del red carpet."),
    ("Guest pass de cameo", "Trae a un amigo… o a tu stunt double."),
    ("Locker con glitter", "Brilla aunque el workout no."),
]


class Command(BaseCommand):
    help = "Create PulseFit catalog: famous coaches/socios, studio, plans and promo codes."

    def handle(self, *args, **options):
        studio, room = self._studio()
        benefits = self._benefits()
        plans = self._plans(benefits)
        self._promos()
        instructors = self._people()
        self._wallets(plans)
        self.stdout.write(
            self.style.SUCCESS(
                f"Demo catalog listo: {len(instructors)} coaches famosos, "
                f"{len(MEMBERS)} socios, studio {studio.name}, sala {room.name}."
            )
        )

    def _studio(self):
        address, _ = Address.objects.get_or_create(
            address=DEMO_STUDIO_ADDRESS,
            defaults={
                "latitude": DEMO_STUDIO_LAT,
                "longitude": DEMO_STUDIO_LNG,
            },
        )
        if address.latitude is None:
            address.latitude = DEMO_STUDIO_LAT
            address.longitude = DEMO_STUDIO_LNG
            address.save(update_fields=["latitude", "longitude"])
        studio, _ = Studio.objects.get_or_create(
            name="PulseFit",
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
            name="Sala A",
            defaults={"capacity": 40, "is_active": True},
        )
        if not room.is_active or room.capacity < 40:
            room.is_active = True
            room.capacity = max(room.capacity, 40)
            room.save(update_fields=["is_active", "capacity"])
        Room.objects.get_or_create(
            studio=studio,
            name="Sala Eventos (la alfombra sudada)",
            defaults={"capacity": 48, "is_active": True},
        )
        return studio, room

    def _benefits(self):
        rows = []
        for name, description in BENEFITS:
            benefit, _ = Benefit.objects.get_or_create(
                name=name,
                defaults={"description": description, "is_active": True},
            )
            if not benefit.is_active or benefit.description != description:
                benefit.description = description
                benefit.is_active = True
                benefit.save(update_fields=["description", "is_active"])
            rows.append(benefit)
        return rows

    def _plans(self, benefits):
        plans = []
        for name, plan_type, price, days, classes, guests, popular, highlighted in PLANS:
            plan, _ = Plan.objects.get_or_create(
                name=name,
                defaults={
                    "type": plan_type,
                    "price": price,
                    "duration_days": days,
                    "classes_included": classes,
                    "guest_passes_included": guests,
                    "is_active": True,
                    "is_popular": popular,
                    "is_highlighted": highlighted,
                },
            )
            plan.type = plan_type
            plan.price = price
            plan.duration_days = days
            plan.classes_included = classes
            plan.guest_passes_included = guests
            plan.is_active = True
            plan.is_popular = popular
            plan.is_highlighted = highlighted
            plan.save()
            plan.benefits.set(benefits[: 2 + guests])
            plans.append(plan)
        return plans

    def _promos(self):
        now = timezone.now()
        for code, description, discount_type, value in PROMO_CODES:
            promo, _ = PromoCode.objects.get_or_create(
                code=code,
                defaults={
                    "description": description,
                    "is_active": True,
                    "valid_from": now - timedelta(days=30),
                    "valid_until": now + timedelta(days=400),
                    "discount_type": discount_type,
                    "discount_value": Decimal(value),
                },
            )
            promo.description = description
            promo.is_active = True
            promo.valid_until = now + timedelta(days=400)
            promo.save()

    def _people(self):
        instructors = []
        for persona in INSTRUCTORS:
            user, created = User.objects.get_or_create(
                username=persona.username,
                defaults=persona_user_defaults(persona),
            )
            if created:
                user.set_password("coach1234" if persona.username == "tomasride" else DEMO_PASSWORD)
            apply_persona_user(
                user, persona, preserve_identity=is_preserved_username(user.username)
            )
            instructor, _ = Instructor.objects.get_or_create(user=user)
            apply_persona_instructor(instructor, persona)
            Member.objects.get_or_create(user=user)
            instructors.append(instructor)

        for persona in MEMBERS:
            user, created = User.objects.get_or_create(
                username=persona.username,
                defaults=persona_user_defaults(persona),
            )
            if created:
                user.set_password(DEMO_PASSWORD)
            apply_persona_user(user, persona, preserve_identity=False)
            Member.objects.get_or_create(user=user)

        for user in User.objects.filter(is_removed=False, is_active=True, is_staff=True):
            instructor, created = Instructor.objects.get_or_create(user=user)
            if created and not instructor.tagline:
                instructor.tagline = "Indoor cycling"
                instructor.specialties = ["Ride"]
                instructor.languages = ["Español"]
                instructor.location = "Santiago, Chile"
                instructor.save()
            Member.objects.get_or_create(user=user)
            if is_preserved_username(user.username):
                if not user.phone_number:
                    user.phone_number = "+56900001111"
                if not user.address:
                    user.address = "PulseFit HQ — el de verdad, no un clone de Hollywood"
                if user.height_cm is None:
                    user.height_cm = 178
                if user.seat_height is None:
                    user.seat_height = 80
                if user.seat_distance is None:
                    user.seat_distance = 10
                if user.handlebar_distance is None:
                    user.handlebar_distance = 9
                if user.cycling_shoe_size is None:
                    user.cycling_shoe_size = Decimal("42.0")
                user.save()

        return instructors

    def _wallets(self, plans):
        today = timezone.localdate()
        unlimited = plans[0]
        smart = plans[2]
        for index, user in enumerate(
            User.objects.filter(is_removed=False, is_active=True).order_by("username")
        ):
            wallet, _ = Wallet.objects.get_or_create(user=user)
            plan = unlimited if getattr(user, "is_staff", False) or index % 3 == 0 else smart
            if not PlanPurchase.objects.filter(user=user).exists():
                promo = PromoCode.objects.filter(is_active=True).order_by("code").first()
                PlanPurchase.objects.create(
                    user=user,
                    plan=plan,
                    price_paid=Decimal(str(plan.price)) - Decimal("5000.00"),
                    quantity=1,
                    discount_amount=Decimal("5000.00"),
                    promo_code=promo,
                    payment_method=(
                        plan_constants.PAYMENT_METHOD_WEBPAY
                        if index % 2 == 0
                        else plan_constants.PAYMENT_METHOD_MERCADOPAGO
                    ),
                    activated_since=today - timedelta(days=12 + (index % 20)),
                )
            wallet.active_membership_end_date = today + timedelta(days=80 + (index % 40))
            wallet.is_unlimited_membership_active = plan.name.startswith("Ilimitado")
            wallet.class_credits = 0 if wallet.is_unlimited_membership_active else 8
            wallet.guest_pass_credits = plan.guest_passes_included or 1
            wallet.retail_discount_percentage = Decimal("0.10") if index % 4 == 0 else Decimal("0")
            wallet.is_priority_booker = bool(user.is_staff) or index % 2 == 0
            wallet.can_freeze_membership = wallet.is_unlimited_membership_active
            wallet.is_founders_exclusive = user.username == "kristina.girod"
            wallet.save()
