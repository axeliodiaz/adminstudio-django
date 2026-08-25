"""Load the latest (or given) versioned fixture pack. Idempotent per version."""

from __future__ import annotations

import json
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.users.fixture_packs import PACKS_ROOT
from apps.users.models import LoadedFixturePack


class Command(BaseCommand):
    help = "Load fixtures/packs/<version> into the database if that version is not recorded yet."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pack",
            help="Pack version to load. Defaults to fixtures/packs/LATEST.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Load even if this version was already recorded.",
        )

    def handle(self, *args, **options):
        if os.environ.get("SKIP_DEMO_FIXTURES", "").lower() in {"1", "true", "yes", "on"}:
            self.stdout.write("Skipping load_versioned_fixtures (SKIP_DEMO_FIXTURES).")
            return

        version = (options["pack"] or "").strip() or self._latest_version()
        pack_dir = PACKS_ROOT / version
        manifest_path = pack_dir / "manifest.json"
        if not manifest_path.exists():
            raise CommandError(f"Missing fixture pack manifest: {manifest_path}")

        if not options["force"] and LoadedFixturePack.objects.filter(version=version).exists():
            self.stdout.write(f"Fixture pack {version} already loaded.")
            return

        skip_heavy = os.environ.get("LOAD_HEAVY_FIXTURES", "").lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }
        heavy_cutoff = int(os.environ.get("FIXTURE_HEAVY_ROW_CUTOFF", "5000"))

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest.get("files", []):
            path = pack_dir / entry["file"]
            if not path.exists():
                raise CommandError(f"Missing fixture file: {path}")
            count = int(entry.get("count") or 0)
            if count == 0:
                continue
            if skip_heavy and count > heavy_cutoff:
                self.stdout.write(
                    self.style.WARNING(
                        f"Skipping {entry['model']} ({count} rows) on this instance; "
                        "set LOAD_HEAVY_FIXTURES=1 to force, or rely on seed_* commands."
                    )
                )
                continue
            self.stdout.write(f"Loading {entry['model']} ({count} rows)")
            call_command("loaddata", str(path), verbosity=options["verbosity"])

        LoadedFixturePack.objects.get_or_create(
            version=version,
            defaults={"notes": f"Loaded {len(manifest.get('files', []))} model files."},
        )
        self.stdout.write(self.style.SUCCESS(f"Loaded fixture pack {version}."))

    def _latest_version(self) -> str:
        latest = PACKS_ROOT / "LATEST"
        if latest.exists():
            version = latest.read_text(encoding="utf-8").strip()
            if version:
                return version
        packs = sorted(path.name for path in PACKS_ROOT.glob("v*") if path.is_dir())
        if not packs:
            raise CommandError(f"No fixture packs found in {PACKS_ROOT}")
        return packs[-1]
