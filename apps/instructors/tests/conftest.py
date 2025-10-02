import pytest
from model_bakery import baker


@pytest.fixture
@pytest.mark.django_db
def instructor():
    """A single instructor with an auto-baked related user and valid email."""
    return baker.make("instructors.Instructor", user__email="instr1@example.com")


@pytest.fixture
@pytest.mark.django_db
def another_instructor():
    """Another instructor with its own baked user, for multi-object tests."""
    return baker.make("instructors.Instructor", user__email="instr2@example.com")


@pytest.fixture
@pytest.mark.django_db
def two_instructors():
    """Return two baked Instructor instances as a tuple, each with valid user emails."""
    i1 = baker.make("instructors.Instructor", user__email="list1@example.com")
    i2 = baker.make("instructors.Instructor", user__email="list2@example.com")
    return (i1, i2)


@pytest.fixture
def registration_payload():
    """Default registration payload for view tests (non-DB)."""
    return {
        "email": "view.instructor@example.com",
        "first_name": "View",
        "last_name": "Tester",
        "phone_number": "+1000000000",
        "birthdate": "2000-01-01",
        "address": "123 Street",
    }


@pytest.fixture
def validated_registration_data():
    """Validated registration data used by services tests.

    Kept here to make instructors tests self-contained and avoid relying on users app fixtures.
    """
    return {
        "email": "jane.doe@example.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "phone_number": "+198765432",
        "password": "ignored_password",
    }
