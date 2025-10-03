import datetime

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestMemberViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def payload(self):
        return {
            "email": "new.member@example.com",
            "password": "S3cretPass!",
            "first_name": "New",
            "last_name": "Member",
            "phone_number": "+1234567890",
        }

    def _make_member_schema_mock(self, email="user@example.com"):
        class _UserSchemaLike:
            def __init__(self, email: str):
                self.email = email
                self.first_name = "First"
                self.last_name = "Last"
                self.phone_number = "+1000000000"
                self.created = datetime.datetime.now(datetime.timezone.utc)

            def model_dump(self):
                return {
                    "email": self.email,
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                    "phone_number": self.phone_number,
                    "created": self.created,
                }

        class _MemberSchemaLike:
            def __init__(self, email: str):
                self.user = _UserSchemaLike(email)

        return _MemberSchemaLike(email)

    def test_create_returns_201_when_new_member_created(self, mocker, api_client, payload):
        member_schema = self._make_member_schema_mock(email=payload["email"])
        get_or_create_mock = mocker.patch(
            "apps.members.views.get_or_create_member_user",
            return_value=(member_schema, True),
        )

        url = reverse("member-register")
        resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 201
        get_or_create_mock.assert_called_once()
        # ensure serializer validated data was forwarded (at least email must match)
        called_args, called_kwargs = get_or_create_mock.call_args
        assert called_args
        assert called_args[0]["email"] == payload["email"]
        assert resp.data["email"] == payload["email"]

    def test_create_returns_200_when_member_already_exists(self, mocker, api_client, payload):
        member_schema = self._make_member_schema_mock(email=payload["email"])
        mocker.patch(
            "apps.members.views.get_or_create_member_user",
            return_value=(member_schema, False),
        )

        url = reverse("member-register")
        resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 200
        assert resp.data["email"] == payload["email"]
