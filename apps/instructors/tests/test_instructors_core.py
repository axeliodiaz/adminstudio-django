"""Tests for core instructors module (apps.instructors.instructors)."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from apps.instructors.instructors import (
    get_instructor_from_id,
    get_or_create_instructor_user,
    get_or_create_user,
    instructors_queryset,
)
from apps.instructors.models import Instructor


@pytest.fixture
def core_validated_data():
    return {
        "email": "core.instructor@example.com",
        "first_name": "Core",
        "last_name": "Tester",
        "phone_number": "+12223334444",
        "password": "ignored",
    }


@pytest.mark.django_db
class TestGetOrCreateUser:
    def test_creates_user_when_absent(self, core_validated_data):
        user = get_or_create_user(core_validated_data)
        User = get_user_model()
        assert isinstance(user, User)
        assert user.email == core_validated_data["email"]

    def test_returns_existing_user_when_present(self, core_validated_data):
        # First call creates
        first = get_or_create_user(core_validated_data)
        # Second should return same user
        second = get_or_create_user(core_validated_data)
        assert first.id == second.id


@pytest.mark.django_db
class TestGetOrCreateInstructorUser:
    def test_creates_instructor_and_returns_created_true(self, core_validated_data):
        instructor, created = get_or_create_instructor_user(core_validated_data)
        assert isinstance(instructor, Instructor)
        assert created is True
        assert Instructor.objects.count() == 1

    def test_returns_existing_instructor_on_second_call(self, core_validated_data):
        _ins, created1 = get_or_create_instructor_user(core_validated_data)
        assert created1 is True
        ins2, created2 = get_or_create_instructor_user(core_validated_data)
        assert created2 is False
        assert Instructor.objects.count() == 1
        assert _ins.id == ins2.id


@pytest.mark.django_db
class TestGetInstructorFromId:
    def test_returns_instructor_instance(self):
        User = get_user_model()
        user = User.objects.create_user(username="x", email="x@example.com", password="x")
        inst = Instructor.objects.create(user=user)
        fetched = get_instructor_from_id(inst.id)
        assert fetched.id == inst.id

    def test_raises_object_does_not_exist_with_message(self):
        with pytest.raises(ObjectDoesNotExist) as exc:
            get_instructor_from_id(uuid.uuid4())
        assert str(exc.value) == "Instructor not found."


@pytest.mark.django_db
class TestInstructorsQueryset:
    def test_returns_all_instructors(self):
        User = get_user_model()
        u1 = User.objects.create_user(username="a", email="a@example.com", password="x")
        u2 = User.objects.create_user(username="b", email="b@example.com", password="x")
        i1 = Instructor.objects.create(user=u1)
        i2 = Instructor.objects.create(user=u2)
        qs = instructors_queryset()
        ids = set(qs.values_list("id", flat=True))
        assert i1.id in ids and i2.id in ids
