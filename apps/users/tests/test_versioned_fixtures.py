"""Tests for versioned fixture dump/load and celebrity catalog."""

import gzip
import json

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.instructors.models import Instructor
from apps.users.models import LoadedFixturePack

User = get_user_model()


@pytest.mark.django_db
def test_seed_demo_catalog_creates_kristina_and_preserves_axelio():
    axel = User.objects.create_user(
        username="axelio",
        email="diaz.axelio@gmail.com",
        password="pass1234",
        first_name="Axel",
        last_name="Díaz",
        is_staff=True,
        is_superuser=True,
    )
    call_command("seed_demo_catalog", verbosity=0)
    axel.refresh_from_db()
    assert axel.first_name == "Axel"
    assert axel.last_name == "Díaz"
    axel_instructor = Instructor.objects.get(user=axel)
    assert axel_instructor.instagram_username == "axeliodiaz"
    kristina = User.objects.get(username="kristina.girod")
    assert kristina.first_name == "Kristina"
    instructor = Instructor.objects.get(user=kristina)
    assert instructor.tagline
    assert instructor.instagram_username == "kristinagirod"
    assert instructor.website_url == f"https://{settings.EMAIL_DOMAIN}/coaches/kristina-girod"
    assert kristina.email == f"kristina_girod@{settings.EMAIL_DOMAIN}"
    assert kristina.address
    assert kristina.height_cm
    assert User.objects.filter(username="usain.bolt").exists()
    assert User.objects.filter(username="michelle.obama").exists()


@pytest.mark.django_db
def test_dump_and_load_versioned_fixtures(tmp_path, monkeypatch):
    from apps.users.management.commands import dump_versioned_fixtures, load_versioned_fixtures

    monkeypatch.setattr(dump_versioned_fixtures, "PACKS_ROOT", tmp_path)
    monkeypatch.setattr(load_versioned_fixtures, "PACKS_ROOT", tmp_path)

    call_command("seed_demo_catalog", verbosity=0)
    call_command("dump_versioned_fixtures", pack="vtest", verbosity=0)

    manifest = json.loads((tmp_path / "vtest" / "manifest.json").read_text())
    assert manifest["version"] == "vtest"
    assert (tmp_path / "LATEST").read_text().strip() == "vtest"
    user_file = tmp_path / "vtest" / "users.user.json.gz"
    with gzip.open(user_file, "rt", encoding="utf-8") as handle:
        payload = json.load(handle)
    usernames = {row["fields"]["username"] for row in payload}
    assert "kristina.girod" in usernames
    assert "axelio" not in usernames

    kristina = User.objects.get(username="kristina.girod")
    kristina.first_name = "NOTKRISTINA"
    kristina.save(update_fields=["first_name"])

    LoadedFixturePack.objects.all().delete()
    call_command("load_versioned_fixtures", pack="vtest", verbosity=0)
    kristina.refresh_from_db()
    assert kristina.first_name == "Kristina"
    call_command("load_versioned_fixtures", pack="vtest", verbosity=0)
    assert User.objects.filter(username="kristina.girod").exists()
    call_command("load_versioned_fixtures", pack="vtest", verbosity=0)
    assert LoadedFixturePack.objects.filter(version="vtest").count() == 1


@pytest.mark.django_db
def test_load_skips_schedule_dependents_when_schedules_are_heavy(tmp_path, monkeypatch, capsys):
    from apps.users.management.commands import load_versioned_fixtures

    monkeypatch.setattr(load_versioned_fixtures, "PACKS_ROOT", tmp_path)
    monkeypatch.delenv("LOAD_HEAVY_FIXTURES", raising=False)
    pack = tmp_path / "vheavy"
    pack.mkdir()
    (pack / "users.user.json.gz").write_bytes(gzip.compress(b"[]"))
    (pack / "schedules.schedule.json.gz").write_bytes(gzip.compress(b"[]"))
    (pack / "members.waitlistentry.json.gz").write_bytes(gzip.compress(b"[]"))
    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "version": "vheavy",
                "files": [
                    {"model": "users.user", "file": "users.user.json.gz", "count": 1},
                    {
                        "model": "schedules.schedule",
                        "file": "schedules.schedule.json.gz",
                        "count": 9000,
                    },
                    {
                        "model": "members.waitlistentry",
                        "file": "members.waitlistentry.json.gz",
                        "count": 10,
                    },
                ],
            }
        )
    )
    call_command("load_versioned_fixtures", pack="vheavy", verbosity=1)
    captured = capsys.readouterr().out
    assert "Skipping schedules.schedule" in captured
    assert "Skipping members.waitlistentry" in captured
    assert LoadedFixturePack.objects.filter(version="vheavy").exists()
