import datetime
import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.members.models import Reservation
from apps.members.exceptions import ReservationInvalidStateException


@pytest.mark.django_db
class TestReservationViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def _make_reservation_schema_mock(self, schedule_id: uuid.UUID, member_id: uuid.UUID):
        class _ReservationSchemaLike:
            def __init__(self):
                self.id = uuid.uuid4()
                self.schedule_id = schedule_id
                self.member_id = member_id
                self.status = "RESERVED"
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_create_returns_201_and_payload_forwarded(self, mocker, api_client):
        schedule_id = uuid.uuid4()
        member_id = uuid.uuid4()
        reservation_schema = self._make_reservation_schema_mock(schedule_id, member_id)
        create_res_mock = mocker.patch(
            "apps.members.views.create_reservation", return_value=reservation_schema
        )

        url = reverse("reservation-create")
        payload = {
            "user_id": str(member_id),
            "schedule_id": str(schedule_id),
            "notes": "Bring towel",
        }
        resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 201
        called_args, _ = create_res_mock.call_args
        assert called_args
        assert str(called_args[0]["user_id"]) == payload["user_id"]
        assert str(resp.data["schedule_id"]) == str(schedule_id)


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


@pytest.mark.django_db
class TestReservationViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def _make_reservation_schema_mock(self, schedule_id: uuid.UUID, member_id: uuid.UUID):
        class _ReservationSchemaLike:
            def __init__(self):
                self.id = uuid.uuid4()
                self.schedule_id = schedule_id
                self.member_id = member_id
                self.status = "RESERVED"
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_create_returns_201_and_payload_forwarded(self, mocker, api_client):
        schedule_id = uuid.uuid4()
        member_id = uuid.uuid4()
        reservation_schema = self._make_reservation_schema_mock(schedule_id, member_id)
        create_res_mock = mocker.patch(
            "apps.members.views.create_reservation", return_value=reservation_schema
        )

        url = reverse("reservation-create")
        payload = {
            "user_id": str(member_id),
            "schedule_id": str(schedule_id),
            "notes": "Bring towel",
        }
        resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 201
        called_args, _ = create_res_mock.call_args
        assert called_args
        assert str(called_args[0]["user_id"]) == payload["user_id"]
        assert str(resp.data["schedule_id"]) == str(schedule_id)


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


@pytest.mark.django_db
class TestReservationCancelViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def _make_cancelled_reservation_schema_mock(
        self, reservation_id: uuid.UUID, schedule_id: uuid.UUID, member_id: uuid.UUID
    ):
        class _ReservationSchemaLike:
            def __init__(self):
                self.id = reservation_id
                self.schedule_id = schedule_id
                self.member_id = member_id
                self.status = "CANCELLED"
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_cancel_returns_200_and_payload_forwarded(self, mocker, api_client):
        reservation_id = uuid.uuid4()
        schedule_id = uuid.uuid4()
        member_id = uuid.uuid4()
        reservation_schema = self._make_cancelled_reservation_schema_mock(
            reservation_id, schedule_id, member_id
        )

        cancel_mock = mocker.patch(
            "apps.members.views.cancel_reservation", return_value=reservation_schema
        )

        url = reverse("reservation-cancel", kwargs={"pk": str(reservation_id)})
        resp = api_client.post(url, data={}, format="json")

        assert resp.status_code == 200
        cancel_mock.assert_called_once_with(reservation_id)
        assert str(resp.data["id"]) == str(reservation_id)
        assert resp.data["status"] == "CANCELLED"

    def test_cancel_returns_404_when_not_found(self, mocker, api_client):
        reservation_id = uuid.uuid4()
        mocker.patch("apps.members.views.cancel_reservation", side_effect=Reservation.DoesNotExist)
        url = reverse("reservation-cancel", kwargs={"pk": str(reservation_id)})
        resp = api_client.post(url, data={}, format="json")

        assert resp.status_code == 404
        assert resp.data["detail"] == "Not found."

    def test_cancel_returns_400_when_invalid_state(self, mocker, api_client):
        reservation_id = uuid.uuid4()
        mocker.patch(
            "apps.members.views.cancel_reservation",
            side_effect=ReservationInvalidStateException(
                "Only RESERVED reservations can be cancelled."
            ),
        )
        url = reverse("reservation-cancel", kwargs={"pk": str(reservation_id)})
        resp = api_client.post(url, data={}, format="json")

        assert resp.status_code == 400
        assert resp.data["detail"] == "Only RESERVED reservations can be cancelled."
