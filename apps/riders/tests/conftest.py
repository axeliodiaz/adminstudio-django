import pytest
from model_bakery import baker


# Common emails used across riders tests
@pytest.fixture
def existing_user_email():
    return "jane@example.com"


@pytest.fixture
def rider_existing_email():
    return "rider@example.com"


@pytest.fixture
def rider_missing_email():
    return "nouser@example.com"


# Data payload for creating a new user via riders.services.get_or_create_user
@pytest.fixture
def new_user_data():
    return {"email": "new.user@example.com", "first_name": "New", "last_name": "User"}


# DB objects
@pytest.fixture
@pytest.mark.django_db
def existing_user(existing_user_email):
    return baker.make("users.User", email=existing_user_email)


@pytest.fixture
@pytest.mark.django_db
def rider_user(rider_existing_email):
    return baker.make("users.User", email=rider_existing_email)


@pytest.fixture
@pytest.mark.django_db
def existing_rider(rider_user):
    return baker.make("riders.Rider", user=rider_user)


@pytest.fixture
@pytest.mark.django_db
def user_without_rider(rider_missing_email):
    return baker.make("users.User", email=rider_missing_email)
