"""Access and member list tests for the People module (CYC-399)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from rest_framework import status

from apps.instructors.models import Instructor

User = get_user_model()


@pytest.fixture
def member_client(api_client):
    member = User.objects.create_user(
        username="people.member",
        email="people.member@example.com",
        password="testpass123",
    )
    token = ExpiringToken.objects.create(user=member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def plain_staff_client(api_client):
    staff = User.objects.create_user(
        username="plain.staff",
        email="plain.staff@example.com",
        password="testpass123",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.fixture
def staff_client(api_client):
    staff = User.objects.create_user(
        username="people.admin",
        email="people.admin@example.com",
        password="testpass123",
        is_staff=True,
        is_superuser=True,
    )
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestPeopleModuleView:
    def test_anonymous_gets_401(self, api_client):
        response = api_client.get(reverse("people-module"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_staff_gets_403(self, member_client):
        response = member_client.get(reverse("people-module"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_gets_module_info(self, staff_client):
        response = staff_client.get(reverse("people-module"))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["module"] == "people"
        assert response.data["features"]["member_list"] is True
        assert response.data["features"]["pay_configuration"] is False


@pytest.mark.django_db
class TestPeopleMemberListView:
    def test_anonymous_gets_401(self, api_client):
        response = api_client.get(reverse("people-member-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_staff_gets_403(self, member_client):
        response = member_client.get(reverse("people-member-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_lists_coaches_staff_and_members(self, staff_client):
        coach_user = User.objects.create_user(
            username="people.coach", email="coach@example.com", password="x"
        )
        Instructor.objects.create(user=coach_user)
        User.objects.create_user(username="people.plain", email="plain@example.com", password="x")
        response = staff_client.get(reverse("people-member-list"))
        assert response.status_code == status.HTTP_200_OK
        by_email = {row["email"]: row for row in response.data["results"]}
        assert by_email["coach@example.com"]["roles"] == ["coach"]
        assert by_email["people.admin@example.com"]["roles"] == ["staff"]
        assert by_email["plain@example.com"]["roles"] == ["member"]

    def test_role_filter(self, staff_client):
        coach_user = User.objects.create_user(
            username="people.coach2", email="coach2@example.com", password="x"
        )
        Instructor.objects.create(user=coach_user)
        response = staff_client.get(reverse("people-member-list"), {"role": "coach"})
        emails = {row["email"] for row in response.data["results"]}
        assert emails == {"coach2@example.com"}

    def test_search(self, staff_client):
        User.objects.create_user(
            username="findable",
            email="findable@example.com",
            password="x",
            first_name="Findable",
        )
        response = staff_client.get(reverse("people-member-list"), {"search": "finda"})
        emails = {row["email"] for row in response.data["results"]}
        assert emails == {"findable@example.com"}


@pytest.mark.django_db
class TestAdminOnlyAccess:
    def test_plain_staff_gets_403(self, plain_staff_client):
        response = plain_staff_client.get(reverse("people-module"))
        assert response.status_code == status.HTTP_403_FORBIDDEN
