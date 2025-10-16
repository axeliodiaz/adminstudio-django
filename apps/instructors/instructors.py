"""Core business logic for instructors app.

This module contains pure functions that operate on models and return model instances
or querysets. View-facing layers should live in services.py and convert results to
schemas or response-ready data.
"""

from typing import Tuple

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from apps.instructors.models import Instructor
from apps.users.services import create_user

User = get_user_model()


def get_or_create_user(data: dict) -> User:
    """Get a user by email or create a new one from provided data.

    Args:
        data: Validated data containing at least the 'email' field and optionally
            other user fields required by create_user.

    Returns:
        User: Existing or newly created user instance.
    """
    try:
        user = User.objects.get(email=data["email"])  # type: ignore[index]
    except User.DoesNotExist:
        user = create_user(data)
    return user


def get_or_create_instructor_user(validated_data: dict) -> Tuple[Instructor, bool]:
    """Retrieve or create an Instructor associated with a User.

    Args:
        validated_data: Validated payload used to create/find the associated User.

    Returns:
        (Instructor, created): Tuple with the Instructor instance and a boolean flag
        indicating whether it was created.
    """
    user = get_or_create_user(validated_data)
    instructor, created = Instructor.objects.get_or_create(user=user)
    return instructor, created


def get_instructor_from_id(pk) -> Instructor:
    """Return an Instructor model by primary key or raise ObjectDoesNotExist.

    Args:
        pk: Primary key of the Instructor.

    Raises:
        ObjectDoesNotExist: If the Instructor does not exist.

    Returns:
        Instructor: The matching Instructor instance.
    """
    try:
        return Instructor.objects.get(pk=pk)
    except Instructor.DoesNotExist as exc:
        raise ObjectDoesNotExist("Instructor not found.") from exc


def instructors_queryset():
    """Return a queryset of all instructors."""
    return Instructor.objects.all()
