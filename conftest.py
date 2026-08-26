import os

# Ensure Django settings are configured for pytest even if pytest-django plugin isn't active
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "adminstudio_django.settings")

try:
    import django  # noqa: F401
except Exception:  # pragma: no cover
    django = None

if django and not os.environ.get("_DJANGO_SETUP_DONE"):
    # Avoid repeated setup in sub-processes
    os.environ["_DJANGO_SETUP_DONE"] = "1"
    django.setup()
    try:
        from django.core.management import call_command

        # Run migrations to ensure test DB has required tables
        call_command("migrate", verbosity=0, interactive=False)
    except Exception:
        # In case migrate isn't available for some reason in CI, ignore to not break import
        pass

# Shared pytest fixtures
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
@pytest.mark.django_db
def base_graph():
    """Builds a minimal graph used by multiple tests: member, instructor, room.

    Returns a tuple: (member, instructor, room)
    """
    from django.contrib.auth import get_user_model
    from apps.members.models import Member
    from apps.instructors.models import Instructor
    from apps.studios.models import Address, Studio, Room
    import uuid as _uuid

    User = get_user_model()
    # Member side
    user_member = User.objects.create_user(
        username=f"member_{_uuid.uuid4()}",
        email=f"m_{_uuid.uuid4()}@ex.com",
        password="pass",
    )
    member = Member.objects.create(user=user_member)

    from apps.wallets.models import Wallet

    Wallet.objects.create(user=user_member, class_credits=10)

    # Studio/Room
    address = Address.objects.create(address="Addr")
    studio = Studio.objects.create(name="S1", address=address, is_active=True)
    room = Room.objects.create(studio=studio, name="R1", capacity=10, is_active=True)

    # Instructor side
    user_instr = User.objects.create_user(
        username=f"instr_{_uuid.uuid4()}",
        email=f"i_{_uuid.uuid4()}@ex.com",
        password="pass",
    )
    instructor = Instructor.objects.create(user=user_instr)

    return member, instructor, room
