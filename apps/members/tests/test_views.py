import datetime
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient

from apps.members.models import Reservation, Member
from apps.members.exceptions import ReservationInvalidStateException, InvalidSpotException
from apps.members.schemas import MemberSchema, ReservationSchema
from apps.users.schemas import UserSchema

User = get_user_model()


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
                self.spot = 1
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "spot": self.spot,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_create_returns_201_and_payload_forwarded(self, mocker, api_client):
        schedule_id = uuid.uuid4()
        member_id = uuid.uuid4()
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_schema = self._make_reservation_schema_mock(schedule_id, member_id)
        create_res_mock = mocker.patch(
            "apps.members.views.create_reservation", return_value=reservation_schema
        )

        # Mock schedule with room for serializer validation
        mock_room = mocker.Mock()
        mock_room.capacity = 10
        mock_schedule = mocker.Mock()
        mock_schedule.room = mock_room
        mocker.patch("apps.members.serializers.get_schedule_by_id", return_value=mock_schedule)

        url = reverse("reservations")
        payload = {
            "schedule_id": str(schedule_id),
            "spot": 1,
            "notes": "Bring towel",
        }
        resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 201
        called_args, _ = create_res_mock.call_args
        assert called_args
        assert str(called_args[0]["user_id"]) == str(user.id)
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
        assert called_kwargs.get("is_active") is False
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
                self.spot = 1
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "spot": self.spot,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_create_returns_201_and_payload_forwarded(self, mocker, api_client):
        schedule_id = uuid.uuid4()
        member_id = uuid.uuid4()
        user = User.objects.create_user(
            username="testuser2",
            email="test2@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_schema = self._make_reservation_schema_mock(schedule_id, member_id)
        create_res_mock = mocker.patch(
            "apps.members.views.create_reservation", return_value=reservation_schema
        )

        # Mock schedule with room for serializer validation
        mock_room = mocker.Mock()
        mock_room.capacity = 10
        mock_schedule = mocker.Mock()
        mock_schedule.room = mock_room
        mocker.patch("apps.members.serializers.get_schedule_by_id", return_value=mock_schedule)

        url = reverse("reservations")
        payload = {
            "schedule_id": str(schedule_id),
            "spot": 1,
            "notes": "Bring towel",
        }
        resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 201
        called_args, _ = create_res_mock.call_args
        assert called_args
        assert str(called_args[0]["user_id"]) == str(user.id)
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
        assert called_kwargs.get("is_active") is False
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

    def test_create_logs_registration_without_raising(self, mocker, api_client, payload, caplog):
        """Regression test: `logger.info(..., extra={...})` must not use a key that
        collides with a reserved `logging.LogRecord` attribute (e.g. "created"),
        which raises `KeyError: "Attempt to overwrite 'created' in LogRecord"`.
        """
        member_schema = self._make_member_schema_mock(email=payload["email"])
        mocker.patch(
            "apps.members.views.get_or_create_member_user",
            return_value=(member_schema, True),
        )

        url = reverse("member-register")
        with caplog.at_level("INFO", logger="apps.members.views"):
            resp = api_client.post(url, data=payload, format="json")

        assert resp.status_code == 201
        matching_records = [
            record for record in caplog.records if record.message == "Member registration processed"
        ]
        assert len(matching_records) == 1
        record = matching_records[0]
        assert record.registration_created is True


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
                self.spot = 1
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "spot": self.spot,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_cancel_returns_200_and_payload_forwarded(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_id = uuid.uuid4()
        schedule_id = uuid.uuid4()
        member_id = uuid.uuid4()
        reservation_schema = self._make_cancelled_reservation_schema_mock(
            reservation_id, schedule_id, member_id
        )

        cancel_mock = mocker.patch(
            "apps.members.views.cancel_reservation", return_value=reservation_schema
        )

        url = reverse("reservation-cancel")
        resp = api_client.post(url, data={"reservation_id": str(reservation_id)}, format="json")

        assert resp.status_code == 200
        cancel_mock.assert_called_once_with(reservation_id)
        assert str(resp.data["id"]) == str(reservation_id)
        assert resp.data["status"] == "CANCELLED"
        assert resp.data["message"] == "Reservation cancelled successfully."

    def test_cancel_returns_404_when_not_found(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_id = uuid.uuid4()
        mocker.patch("apps.members.views.cancel_reservation", side_effect=Reservation.DoesNotExist)
        url = reverse("reservation-cancel")
        resp = api_client.post(url, data={"reservation_id": str(reservation_id)}, format="json")

        assert resp.status_code == 404
        assert resp.data["detail"] == "Not found."

    def test_cancel_returns_400_when_invalid_state(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_id = uuid.uuid4()
        mocker.patch(
            "apps.members.views.cancel_reservation",
            side_effect=ReservationInvalidStateException(
                "Only RESERVED reservations can be cancelled."
            ),
        )
        url = reverse("reservation-cancel")
        resp = api_client.post(url, data={"reservation_id": str(reservation_id)}, format="json")

        assert resp.status_code == 400
        assert resp.data["detail"] == "Only RESERVED reservations can be cancelled."


@pytest.mark.django_db
class TestReservationCheckInViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_check_in_returns_updated_reservation(self, mocker, api_client):
        user = User.objects.create_user(
            username="checkin-user",
            email="checkin@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_id = uuid.uuid4()
        updated = mocker.Mock()
        updated.model_dump.return_value = {
            "id": str(reservation_id),
            "status": "ATTENDED",
        }
        check_in = mocker.patch(
            "apps.members.views.check_in_member_reservation",
            return_value=updated,
        )

        response = api_client.post(
            reverse("reservation-check-in", kwargs={"reservation_id": reservation_id}),
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "ATTENDED"
        check_in.assert_called_once_with(str(reservation_id), user.id)

    def test_check_in_returns_404_for_non_owned_reservation(self, mocker, api_client):
        user = User.objects.create_user(
            username="checkin-other",
            email="checkin-other@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        reservation_id = uuid.uuid4()
        mocker.patch(
            "apps.members.views.check_in_member_reservation",
            side_effect=Reservation.DoesNotExist,
        )

        response = api_client.post(
            reverse("reservation-check-in", kwargs={"reservation_id": reservation_id}),
            format="json",
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestReservationsList:

    def test_list_returns_200_and_payload_forwarded(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        # Create member for the user (required by the view)
        member = Member.objects.create(user=user)
        api_client.force_authenticate(user=user)
        # Arrange
        start_date = datetime.date(2025, 1, 1)
        end_date = datetime.date(2025, 1, 31)
        instructor_id = uuid.uuid4()
        room_id = uuid.uuid4()

        now = datetime.datetime.now(datetime.timezone.utc)
        schemas = [
            ReservationSchema(
                id=uuid.uuid4(),
                created=now,
                modified=now,
                schedule_id=uuid.uuid4(),
                member_id=member.id,
                status="RESERVED",
                spot=1,
                notes="",
            ),
            ReservationSchema(
                id=uuid.uuid4(),
                created=now,
                modified=now,
                schedule_id=uuid.uuid4(),
                member_id=member.id,
                status="RESERVED",
                spot=2,
                notes="",
            ),
        ]
        list_mock = mocker.patch("apps.members.views.list_reservations", return_value=schemas)

        # Act
        url = reverse("reservations")
        resp = api_client.get(
            url,
            data={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "schedule__instructor_id": str(instructor_id),
                "schedule__room_id": str(room_id),
            },
        )

        # Assert
        assert resp.status_code == 200
        list_mock.assert_called_once()
        assert isinstance(resp.data, list)
        assert len(resp.data) == 2
        assert str(resp.data[0]["member_id"]) == str(member.id)
        assert {"id", "schedule_id", "member_id", "status", "spot"}.issubset(resp.data[0].keys())

    def test_list_defaults_dates_and_member_when_not_provided(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser-defaults",
            email="test-defaults@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)

        # Create a member linked to this user
        member = Member.objects.create(user=user)

        schemas = []
        list_mock = mocker.patch("apps.members.views.list_reservations", return_value=schemas)

        url = reverse("reservations")
        resp = api_client.get(url)

        assert resp.status_code == 200
        assert resp.data == []
        list_mock.assert_called_once()

        # Ensure start_date, end_date and member_id were provided to the service
        called_args, _ = list_mock.call_args
        assert called_args
        query = called_args[0]
        assert "start_date" in query
        assert "end_date" in query
        assert "member_id" in query
        assert str(query["member_id"]) == str(member.id)

    def test_list_returns_400_when_invalid_query(self, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        Member.objects.create(user=user)
        api_client.force_authenticate(user=user)
        # Test invalid date range: start_date > end_date
        url = reverse("reservations")
        resp = api_client.get(
            url,
            data={
                "start_date": datetime.date(2025, 1, 31).isoformat(),
                "end_date": datetime.date(2025, 1, 1).isoformat(),  # end_date before start_date
            },
        )

        assert resp.status_code == 400


@pytest.mark.django_db
class TestReservationChangeSpotViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    def _make_reservation_schema_mock(
        self, reservation_id: uuid.UUID, schedule_id: uuid.UUID, member_id: uuid.UUID, spot: int = 5
    ):
        class _ReservationSchemaLike:
            def __init__(self):
                self.id = reservation_id
                self.schedule_id = schedule_id
                self.member_id = member_id
                self.status = "RESERVED"
                self.spot = spot
                self.notes = ""

            def model_dump(self):
                return {
                    "id": self.id,
                    "schedule_id": self.schedule_id,
                    "member_id": self.member_id,
                    "status": self.status,
                    "spot": self.spot,
                    "notes": self.notes,
                }

        return _ReservationSchemaLike()

    def test_change_spot_returns_200_and_payload_forwarded(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        schedule_id = uuid.uuid4()
        reservation_id = uuid.uuid4()
        member_id = uuid.uuid4()
        reservation_schema = self._make_reservation_schema_mock(
            reservation_id, schedule_id, member_id, spot=5
        )

        change_spot_mock = mocker.patch(
            "apps.members.views.change_reservation_spot", return_value=reservation_schema
        )

        url = reverse("reservation-change-spot", kwargs={"schedule_id": str(schedule_id)})
        payload = {"new_spot": 5}
        resp = api_client.patch(url, data=payload, format="json")

        assert resp.status_code == 200
        change_spot_mock.assert_called_once_with(schedule_id, str(user.id), 5)
        assert str(resp.data["id"]) == str(reservation_id)
        assert resp.data["spot"] == 5

    def test_change_spot_returns_404_when_not_found(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        schedule_id = uuid.uuid4()
        mocker.patch(
            "apps.members.views.change_reservation_spot", side_effect=Reservation.DoesNotExist
        )
        url = reverse("reservation-change-spot", kwargs={"schedule_id": str(schedule_id)})
        payload = {"new_spot": 5}
        resp = api_client.patch(url, data=payload, format="json")

        assert resp.status_code == 404
        assert resp.data["detail"] == "Not found."

    def test_change_spot_returns_400_when_invalid_state(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        schedule_id = uuid.uuid4()
        mocker.patch(
            "apps.members.views.change_reservation_spot",
            side_effect=ReservationInvalidStateException(
                "Only RESERVED reservations can change spots."
            ),
        )
        url = reverse("reservation-change-spot", kwargs={"schedule_id": str(schedule_id)})
        payload = {"new_spot": 5}
        resp = api_client.patch(url, data=payload, format="json")

        assert resp.status_code == 400
        assert resp.data["detail"] == "Only RESERVED reservations can change spots."

    def test_change_spot_returns_400_when_invalid_spot(self, mocker, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        schedule_id = uuid.uuid4()
        mocker.patch(
            "apps.members.views.change_reservation_spot",
            side_effect=InvalidSpotException("Spot 5 is already taken."),
        )
        url = reverse("reservation-change-spot", kwargs={"schedule_id": str(schedule_id)})
        payload = {"new_spot": 5}
        resp = api_client.patch(url, data=payload, format="json")

        assert resp.status_code == 400
        assert resp.data["detail"] == "Spot 5 is already taken."

    def test_change_spot_returns_400_when_invalid_serializer(self, api_client):
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        api_client.force_authenticate(user=user)
        schedule_id = uuid.uuid4()
        url = reverse("reservation-change-spot", kwargs={"schedule_id": str(schedule_id)})
        # Missing new_spot or invalid value
        payload = {}
        resp = api_client.patch(url, data=payload, format="json")

        assert resp.status_code == 400
