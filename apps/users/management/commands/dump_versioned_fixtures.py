"""Dump demo data as versioned per-model fixture files."""

from __future__ import annotations

import gzip
import json
from datetime import date
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Q

from apps.users.demo_catalog import PRESERVED_USERNAMES, demo_usernames
from apps.users.fixture_packs import MODEL_LABELS, PACKS_ROOT

DASHBOARD_CLASS_DESCRIPTION = "Clase demo dashboard"


class Command(BaseCommand):
    help = "Dump demo/catalog rows into fixtures/packs/<version>/, one gzip JSON file per model."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pack",
            default=f"v{date.today().isoformat().replace('-', '')}",
            help="Pack version folder (default: vYYYYMMDD).",
        )
        parser.add_argument(
            "--seed",
            action="store_true",
            help="Run catalog + coach + dashboard seeds first.",
        )

    def handle(self, *args, **options):
        version = options["pack"].strip()
        if options["seed"]:
            for name in (
                "apps/legal/fixtures/legal.json",
                "apps/faqs/fixtures/faq.json",
            ):
                path = Path(settings.BASE_DIR) / name
                if path.exists():
                    call_command("loaddata", str(path), verbosity=options["verbosity"])
            call_command("seed_demo_catalog", verbosity=options["verbosity"])
            call_command("seed_coach_demo", verbosity=options["verbosity"])
            call_command("seed_dashboard_demo", verbosity=options["verbosity"])

        pack_dir = PACKS_ROOT / version
        pack_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for label in MODEL_LABELS:
            queryset = self._queryset(label)
            payload = serializers.serialize("json", queryset)
            filename = f"{label}.json.gz"
            path = pack_dir / filename
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(payload)
            count = queryset.count()
            files.append({"model": label, "file": filename, "count": count})
            self.stdout.write(f"{label}: {count} → {filename}")

        manifest = {
            "version": version,
            "created": date.today().isoformat(),
            "files": files,
        }
        (pack_dir / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        (PACKS_ROOT / "LATEST").write_text(version + "\n", encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Wrote fixture pack {pack_dir}"))

    def _user_q(self, prefix: str = "username"):
        demo_names = demo_usernames()
        return (Q(**{f"{prefix}__in": demo_names}) | Q(**{f"{prefix}__startswith": "demo."})) & ~Q(
            **{f"{prefix}__in": PRESERVED_USERNAMES}
        )

    def _queryset(self, label: str):
        model = apps.get_model(label)
        if label == "users.user":
            return (
                model.objects.filter(self._user_q()).filter(is_superuser=False).order_by("username")
            )
        if label == "instructors.instructor":
            return model.objects.filter(self._user_q("user__username")).order_by("pk")
        if label == "members.member":
            return model.objects.filter(self._user_q("user__username")).order_by("pk")
        if label in {"wallets.wallet", "wallets.planpurchase", "notifications.notification"}:
            return model.objects.filter(self._user_q("user__username")).order_by("pk")
        if label == "schedules.schedule":
            return (
                model.objects.filter(
                    Q(description__startswith="demo.coach")
                    | Q(description=DASHBOARD_CLASS_DESCRIPTION)
                )
                .exclude(instructor__user__username__in=PRESERVED_USERNAMES)
                .order_by("start_time")
            )
        if label in {"members.reservation", "members.waitlistentry"}:
            return (
                model.objects.filter(
                    Q(schedule__description__startswith="demo.coach")
                    | Q(schedule__description=DASHBOARD_CLASS_DESCRIPTION)
                )
                .exclude(schedule__instructor__user__username__in=PRESERVED_USERNAMES)
                .order_by("pk")
            )
        if label == "coach.playlisttemplate":
            return model.objects.filter(self._user_q("instructor__user__username")).order_by("pk")
        if label == "coach.classplaylist":
            return (
                model.objects.filter(schedule__description__startswith="demo.coach")
                .exclude(instructor__user__username__in=PRESERVED_USERNAMES)
                .order_by("pk")
            )
        if label == "coach.playlistsegment":
            return (
                model.objects.filter(playlist__schedule__description__startswith="demo.coach")
                .exclude(playlist__instructor__user__username__in=PRESERVED_USERNAMES)
                .order_by("pk")
            )
        if label == "coach.playlisttrack":
            return (
                model.objects.filter(
                    segment__playlist__schedule__description__startswith="demo.coach"
                )
                .exclude(segment__playlist__instructor__user__username__in=PRESERVED_USERNAMES)
                .order_by("pk")
            )
        if label == "coach.classrating":
            return (
                model.objects.filter(schedule__description__startswith="demo.coach")
                .exclude(schedule__instructor__user__username__in=PRESERVED_USERNAMES)
                .order_by("pk")
            )
        return model.objects.all().order_by("pk")
