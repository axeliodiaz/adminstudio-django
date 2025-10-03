import secrets
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from apps.users.schemas import UserSchema

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
        # apps.users.services.create_user now supports optional password
        user = create_user(data)
    return user
