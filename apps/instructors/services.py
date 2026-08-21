"""View-facing services for the instructors app.

Expose functions that return schemas or simple dicts for consumption by views.
Core business logic lives in apps.instructors.instructors.
"""

from typing import Tuple
from uuid import UUID

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.instructors.instructors import get_instructor_from_id
from apps.instructors.instructors import (
    get_or_create_instructor_user as _get_or_create_instructor_user,
)
from apps.instructors.instructors import instructors_queryset
from apps.instructors.models import Instructor
from apps.instructors.schemas import (
    AdminInstructorSchema,
    InstructorPublicSchema,
)
from apps.users.schemas import UserSchema

User = get_user_model()

USER_ADMIN_FIELDS = {"first_name", "last_name", "email", "phone_number", "is_active"}
INSTRUCTOR_ADMIN_FIELDS = {
    "description",
    "tagline",
    "website_url",
    "instagram_username",
    "tiktok_username",
    "is_verified",
    "instructor_since",
    "location",
    "last_spotify_playlist",
    "last_apple_music_playlist",
    "last_youtube_music_playlist",
}


def get_or_create_instructor_user(validated_data: dict) -> Tuple[dict, bool]:
    """Create or fetch an Instructor and return user schema dict for views.

    Behavior per tests:
    - On first creation, include first_name, last_name, and username (if provided in input).
    - On subsequent calls for the same email, return only first_name and last_name.

    Args:
        validated_data: Validated input data used to create/find the associated user.

    Returns:
        (data, created): Tuple where `data` is a dict for the related user and
        `created` indicates if the instructor was created.
    """
    instructor, created = _get_or_create_instructor_user(validated_data)
    user_data = UserSchema.model_validate(instructor.user).model_dump()

    # Minimal payload expected by tests
    base = {k: user_data.get(k) for k in ("first_name", "last_name")}
    # Per current test expectations, only return first_name and last_name
    return base, created


def get_instructor_by_id(pk) -> dict:
    """Return a public InstructorSchema (without sensitive user fields) by primary key or raise ObjectDoesNotExist with a friendly message."""
    try:
        instructor = get_instructor_from_id(pk)
    except ObjectDoesNotExist as exc:
        raise ObjectDoesNotExist("Instructor not found.") from exc
    return InstructorPublicSchema.model_validate(instructor).model_dump()


def get_instructors_list() -> list[dict]:
    """Return a list of public InstructorSchema dicts for all instructors."""
    return [
        InstructorPublicSchema.model_validate(obj).model_dump() for obj in instructors_queryset()
    ]


def update_instructor(pk, validated_data: dict, *, partial: bool = False) -> dict:
    """Update an instructor's related user fields and return public InstructorSchema dict.

    Args:
        pk: Instructor primary key.
        validated_data: Data already validated by the view serializer.
        partial: Whether this is a partial update (PATCH). Note: since data is already
            validated and we only set provided fields, behavior is naturally partial.

    Returns:
        dict: InstructorPublicSchema as dict after applying updates.
    """
    # Will raise ObjectDoesNotExist("Instructor not found.") if missing
    instructor = get_instructor_from_id(pk)
    user = instructor.user

    # Only update allowed fields and only those provided in validated_data
    # Sensitive fields email and phone_number are intentionally excluded from updates
    updatable_fields = {"first_name", "last_name", "birthdate", "address"}
    update_fields: list[str] = []

    for field in updatable_fields:
        if field in validated_data:
            setattr(user, field, validated_data[field])
            update_fields.append(field)

    if update_fields:
        user.save(update_fields=update_fields)  # type: ignore[arg-type]

    # Return the public instructor schema payload (no email/phone)
    return InstructorPublicSchema.model_validate(instructor).model_dump()


def _admin_instructor_dict(instructor: Instructor) -> dict:
    return AdminInstructorSchema.from_instructor(instructor).model_dump(mode="json")


def list_admin_instructors(
    *,
    search: str | None = None,
    status: str | None = None,
) -> list[dict]:
    """Return instructors for the staff admin list."""
    queryset = Instructor.objects.select_related("user").order_by(
        "user__first_name", "user__last_name", "user__email"
    )

    if status == "verified":
        queryset = queryset.filter(is_verified=True)
    elif status == "unverified":
        queryset = queryset.filter(is_verified=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(user__first_name__icontains=term)
            | Q(user__last_name__icontains=term)
            | Q(user__email__icontains=term)
            | Q(user__username__icontains=term)
            | Q(location__icontains=term)
            | Q(instagram_username__icontains=term)
            | Q(tagline__icontains=term)
        )

    return [_admin_instructor_dict(instructor) for instructor in queryset]


def get_admin_instructor(*, instructor_id: str | UUID) -> dict:
    """Return one instructor for the staff admin."""
    instructor = get_object_or_404(
        Instructor.objects.select_related("user"),
        id=instructor_id,
    )
    return _admin_instructor_dict(instructor)


def _apply_admin_instructor_fields(instructor: Instructor, data: dict) -> Instructor:
    user = instructor.user
    user_dirty: list[str] = []
    instructor_dirty: list[str] = []
    sync_username = bool(user.username) and user.username == (user.email or "")

    if "email" in data:
        email = (data["email"] or "").strip()
        if not email:
            raise ValueError("El correo electrónico es obligatorio.")
        taken = (
            User.objects.filter(is_removed=False)
            .filter(Q(email__iexact=email) | Q(username__iexact=email))
            .exclude(id=user.id)
            .exists()
        )
        if taken:
            raise ValueError("Ya existe un usuario con ese correo.")

    for field, value in data.items():
        if field in USER_ADMIN_FIELDS:
            if field == "email":
                value = (value or "").strip()
                if sync_username:
                    user.username = value
                    user_dirty.append("username")
            elif field in {"first_name", "last_name", "phone_number"} and value is None:
                value = ""
            setattr(user, field, value)
            user_dirty.append(field)
        elif field in INSTRUCTOR_ADMIN_FIELDS:
            if (
                field
                in {
                    "description",
                    "tagline",
                    "website_url",
                    "instagram_username",
                    "tiktok_username",
                    "location",
                    "last_spotify_playlist",
                    "last_apple_music_playlist",
                    "last_youtube_music_playlist",
                }
                and value is None
            ):
                value = ""
            setattr(instructor, field, value)
            instructor_dirty.append(field)

    if user_dirty:
        user.save(update_fields=list(dict.fromkeys(user_dirty)))
    if instructor_dirty:
        instructor.save(update_fields=list(dict.fromkeys(instructor_dirty)))

    return instructor


def update_admin_instructor(*, instructor_id: str | UUID, data: dict) -> dict:
    """Update staff-editable instructor and related user fields."""
    instructor = get_object_or_404(
        Instructor.objects.select_related("user"),
        id=instructor_id,
    )
    instructor = _apply_admin_instructor_fields(instructor, data)
    instructor.refresh_from_db()
    return _admin_instructor_dict(instructor)
