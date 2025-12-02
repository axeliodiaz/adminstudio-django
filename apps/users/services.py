import secrets
from uuid import UUID
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from apps.users.schemas import UserSchema, UserProfileSchema, UserProfileResponseSchema

User = get_user_model()


def create_user(validated_data: dict) -> User:
    """
    Service to create a User from validated registration data.

    Expected validated_data keys: email?, first_name?, last_name?, phone_number?, password?
    Behavior:
    - If a password is provided, it is used as-is.
    - Otherwise, a secure random password is generated server-side.
    Returns the created User instance.
    """
    provided_password = (validated_data.get("password") or "").strip()
    password = provided_password or secrets.token_urlsafe(settings.DEFAULT_PASSWORD_LENGTH)
    email = validated_data.get("email") or ""
    first_name = validated_data.get("first_name", "")
    last_name = validated_data.get("last_name", "")
    phone_number = (validated_data.get("phone_number") or "").strip()

    user = User.objects.create_user(
        username=email,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    # Only set and save phone_number if it is non-empty
    if phone_number:
        user.phone_number = phone_number
        user.save(update_fields=["phone_number"])  # type: ignore[arg-type]
    return user


def get_user_from_id(id: str | UUID) -> dict[str, str | int]:
    """
    Fetches and serializes a user object based on the provided unique identifier.

    This function retrieves a user record from the database using the supplied
    ID. If the specified user does not exist, it returns a 404 error. The
    retrieved user object is then serialized into a dictionary format.

    Parameters:
    id: str | UUID
        The unique identifier of the user that needs to be fetched. The ID
        can be provided either as a string or a UUID instance.

    Returns:
    dict[str, str | int]
        A dictionary containing serialized user data.
    """
    user = get_object_or_404(User, id=id)
    return UserSchema.model_validate(user).model_dump()


def get_or_create_user(data: dict) -> User:
    try:
        user = User.objects.get(email=data["email"])
    except User.DoesNotExist:
        user = create_user(data)
    return user


def get_user_profile(user: User) -> UserProfileResponseSchema:
    """
    Return the user's profile structured by categories.
    """
    return UserProfileResponseSchema.from_user(user)


def update_user_profile(user: User, profile_data: dict[str, Any]) -> UserProfileResponseSchema:
    """
    Update the user's profile data using only allowed fields.
    """
    # Fields that can be updated from the profiles endpoint.
    # Important: email, username and phone_number are NOT updated here.
    allowed_fields = {
        # Personal info
        "first_name",
        "last_name",
        "gender",
        "birthdate",
        "height_cm",
        "weight_kg",
        "address",
        # Cycling
        "seat_height",
        "seat_distance",
        "handlebar_distance",
        "cycling_shoe_size",
    }

    dirty_fields: list[str] = []
    for field, value in profile_data.items():
        if field in allowed_fields:
            setattr(user, field, value)
            dirty_fields.append(field)

    if dirty_fields:
        user.save(update_fields=dirty_fields)

    return UserProfileResponseSchema.from_user(user)


def change_user_password(user: User, old_password: str, new_password: str) -> None:
    """
    Change the user's password after validating the current password.

    Args:
        user: The user whose password will be changed.
        old_password: The user's current password.
        new_password: The new password to set.

    Raises:
        ValueError: If the current password is not valid.
    """
    if not user.check_password(old_password):
        raise ValueError("Contraseña actual incorrecta.")

    user.set_password(new_password)
    user.save(update_fields=["password"])
