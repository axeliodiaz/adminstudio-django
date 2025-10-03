import pytest
from model_bakery import baker


# Common emails used across members tests
@pytest.fixture
def existing_user_email():
    return "jane@example.com"


@pytest.fixture
def member_existing_email():
    return "member@example.com"


@pytest.fixture
def member_missing_email():
    return "nouser@example.com"


# Data payload for creating a new user via members.services.get_or_create_user
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
def member_user(member_existing_email):
    return baker.make("users.User", email=member_existing_email)


@pytest.fixture
@pytest.mark.django_db
def existing_member(member_user):
    return baker.make("members.Member", user=member_user)


@pytest.fixture
@pytest.mark.django_db
def user_without_member(member_missing_email):
    return baker.make("users.User", email=member_missing_email)
