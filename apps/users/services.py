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

    Expected validated_data keys: email?, first_name?, last_name?, phone?
    Note: The provided password (if any) is ignored; a random password is generated server-side.
    Returns the created User instance.
    """
    # Generate a random secure password instead of using provided one
    random_password = secrets.token_urlsafe(settings.DEFAULT_PASSWORD_LENGTH)
    email = validated_data.get("email") or ""
    first_name = validated_data.get("first_name", "")
    last_name = validated_data.get("last_name", "")
    phone = validated_data.get("phone", "")

    user = User.objects.create_user(
        username=email,
        password=random_password,
        email=email,
        first_name=first_name,
        last_name=last_name,
    )
    # Set phone if the custom user model has such a field
    if hasattr(user, "phone"):
        setattr(user, "phone", phone)
        user.save(update_fields=["phone"])  # type: ignore[arg-type]
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
