import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.instructors.models import Instructor

User = get_user_model()


@pytest.fixture
def staff_client(api_client):
    staff_user = User.objects.create_user(
        username="adminuser",
        email="admin@example.com",
        password="testpass123",
        is_staff=True,
    )
    token = ExpiringToken.objects.create(user=staff_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client, staff_user


@pytest.mark.django_db
class TestAdminInstructorListView:
    def test_requires_authentication(self, api_client):
        response = api_client.get(reverse("admin-instructors"))
        assert response.status_code == 401

    def test_requires_staff(self, api_client):
        member = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="testpass123",
        )
        token = ExpiringToken.objects.create(user=member)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(reverse("admin-instructors"))

        assert response.status_code == 403

    def test_returns_list_for_staff(self, staff_client, instructor, another_instructor):
        client, _ = staff_client
        response = client.get(reverse("admin-instructors"))

        assert response.status_code == 200
        ids = {row["id"] for row in response.data}
        assert str(instructor.id) in ids
        assert str(another_instructor.id) in ids
        assert "email" in response.data[0]
        assert "is_verified" in response.data[0]

    def test_filters_by_status_and_search(self, staff_client):
        client, _ = staff_client
        verified = baker.make(
            "instructors.Instructor",
            user__email="verified@example.com",
            user__first_name="Ana",
            is_verified=True,
        )
        baker.make(
            "instructors.Instructor",
            user__email="other@example.com",
            user__first_name="Bob",
            is_verified=False,
        )

        verified_response = client.get(reverse("admin-instructors"), {"status": "verified"})
        assert verified_response.status_code == 200
        assert all(row["is_verified"] is True for row in verified_response.data)
        assert str(verified.id) in {row["id"] for row in verified_response.data}

        search_response = client.get(reverse("admin-instructors"), {"search": "Ana"})
        assert search_response.status_code == 200
        assert [row["email"] for row in search_response.data] == ["verified@example.com"]

    def test_create_instructor(self, staff_client):
        client, _ = staff_client
        payload = {
            "email": "new.instructor@example.com",
            "first_name": "Luna",
            "last_name": "Rider",
            "tagline": "Indoor cycling",
            "is_verified": True,
            "location": "Santiago",
        }

        response = client.post(reverse("admin-instructors"), data=payload, format="json")

        assert response.status_code == 201
        assert response.data["email"] == "new.instructor@example.com"
        assert response.data["tagline"] == "Indoor cycling"
        assert response.data["is_verified"] is True
        assert Instructor.objects.filter(user__email="new.instructor@example.com").exists()

    def test_create_rejects_duplicate_email(self, staff_client, instructor):
        client, _ = staff_client
        response = client.post(
            reverse("admin-instructors"),
            data={"email": instructor.user.email, "first_name": "Dup"},
            format="json",
        )

        assert response.status_code == 400
        assert "Ya existe un instructor" in response.data["detail"]


@pytest.mark.django_db
class TestAdminInstructorDetailView:
    def test_detail_requires_staff(self, api_client, instructor):
        member = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="testpass123",
        )
        token = ExpiringToken.objects.create(user=member)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = api_client.get(
            reverse("admin-instructor-detail", kwargs={"instructor_id": instructor.id})
        )

        assert response.status_code == 403

    def test_detail_returns_instructor(self, staff_client, instructor):
        client, _ = staff_client
        response = client.get(
            reverse("admin-instructor-detail", kwargs={"instructor_id": instructor.id})
        )

        assert response.status_code == 200
        assert response.data["id"] == str(instructor.id)
        assert response.data["email"] == instructor.user.email

    def test_patch_updates_fields(self, staff_client, instructor):
        client, _ = staff_client
        url = reverse("admin-instructor-detail", kwargs={"instructor_id": instructor.id})

        response = client.patch(
            url,
            data={
                "first_name": "Camila",
                "last_name": "Rojas",
                "tagline": "Ride hard",
                "instagram_username": "camila.ride",
                "is_verified": True,
                "location": "Providencia",
            },
            format="json",
        )

        assert response.status_code == 200
        assert response.data["first_name"] == "Camila"
        assert response.data["tagline"] == "Ride hard"
        assert response.data["instagram_username"] == "camila.ride"
        assert response.data["is_verified"] is True

        instructor.refresh_from_db()
        instructor.user.refresh_from_db()
        assert instructor.user.first_name == "Camila"
        assert instructor.tagline == "Ride hard"
        assert instructor.is_verified is True
