"""View-facing services for the instructors app.

Expose functions that return schemas or simple dicts for consumption by views.
Core business logic lives in apps.instructors.instructors.
"""

from typing import Tuple

from django.core.exceptions import ObjectDoesNotExist

from apps.instructors.instructors import get_instructor_from_id
from apps.instructors.instructors import (
    get_or_create_instructor_user as _get_or_create_instructor_user,
)
from apps.instructors.instructors import instructors_queryset
from apps.instructors.schemas import InstructorSchema
from apps.users.schemas import UserSchema


def get_or_create_instructor_user(validated_data: dict) -> Tuple[dict, bool]:
    """Create or fetch an Instructor and return user schema dict for views.

    Args:
        validated_data: Validated input data used to create/find the associated user.

    Returns:
        (data, created): Tuple where `data` is a dict produced by UserSchema
        for the related user, and `created` indicates if the instructor was created.
    """
    instructor, created = _get_or_create_instructor_user(validated_data)
    data = UserSchema.model_validate(instructor.user).model_dump()
    return data, created


def get_instructor_by_id(pk) -> dict:
    """Return an InstructorSchema as dict by primary key or raise ObjectDoesNotExist with a friendly message."""
    try:
        instructor = get_instructor_from_id(pk)
    except ObjectDoesNotExist as exc:
        raise ObjectDoesNotExist("Instructor not found.") from exc
    return InstructorSchema.model_validate(instructor).model_dump()


def get_instructors_list() -> list[dict]:
    """Return a list of InstructorSchema dicts for all instructors."""
    return [InstructorSchema.model_validate(obj).model_dump() for obj in instructors_queryset()]


def update_instructor(pk, validated_data: dict, *, partial: bool = False) -> dict:
    """Update an instructor's related user fields and return InstructorSchema dict.

    Args:
        pk: Instructor primary key.
        validated_data: Data already validated by the view serializer.
        partial: Whether this is a partial update (PATCH). Note: since data is already
            validated and we only set provided fields, behavior is naturally partial.

    Returns:
        dict: InstructorSchema as dict after applying updates.
    """
    # Will raise ObjectDoesNotExist("Instructor not found.") if missing
    instructor = get_instructor_from_id(pk)
    user = instructor.user

    # Only update allowed fields and only those provided in validated_data
    updatable_fields = {"first_name", "last_name", "email", "phone_number", "birthdate", "address"}
    update_fields: list[str] = []

    for field in updatable_fields:
        if field in validated_data:
            setattr(user, field, validated_data[field])
            update_fields.append(field)

    if update_fields:
        user.save(update_fields=update_fields)  # type: ignore[arg-type]

    # Return the instructor schema payload
    return InstructorSchema.model_validate(instructor).model_dump()
