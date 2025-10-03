import pytest
from datetime import datetime, timedelta, timezone
from model_bakery import baker


@pytest.fixture
@pytest.mark.django_db
def room_main():
    return baker.make("studios.Room", name="Main Hall")


@pytest.fixture
@pytest.mark.django_db
def room_small():
    return baker.make("studios.Room", name="Small Studio")


@pytest.fixture
@pytest.mark.django_db
def instructor_alice():
    # Ensure deterministic username and email
    return baker.make(
        "instructors.Instructor",
        user__username="alice",
        user__email="alice@example.com",
    )


@pytest.fixture
@pytest.mark.django_db
def instructor_bob():
    return baker.make(
        "instructors.Instructor",
        user__username="bobby",
        user__email="bob@example.com",
    )


@pytest.fixture
@pytest.mark.django_db
def schedules_sample(instructor_alice, instructor_bob, room_main, room_small):
    # Create a set of schedules spanning different start times, instructors, and rooms
    base = datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc)
    objs = [
        baker.make(
            "schedules.Schedule",
            instructor=instructor_alice,
            room=room_main,
            start_time=base,
            duration_minutes=45,
            status="scheduled",
        ),
        baker.make(
            "schedules.Schedule",
            instructor=instructor_alice,
            room=room_small,
            start_time=base + timedelta(hours=1),
            duration_minutes=30,
            status="scheduled",
        ),
        baker.make(
            "schedules.Schedule",
            instructor=instructor_bob,
            room=room_main,
            start_time=base + timedelta(hours=2),
            duration_minutes=60,
            status="scheduled",
        ),
    ]
    return objs
