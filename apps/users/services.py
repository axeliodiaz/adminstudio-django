import random
import secrets
import string
from datetime import timedelta
from uuid import UUID
from typing import Any

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.users import constants
from apps.users.models import EmailChangeRequest, PasswordResetCode
from apps.users.schemas import (
    UserSchema,
    UserProfileSchema,
    UserProfileResponseSchema,
    AdminUserSchema,
)

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
    is_active = validated_data.get("is_active", True)

    user = User.objects.create_user(
        username=email,
        password=password,
        email=email,
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
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
        "waitlist_auto_confirm",
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


def generate_password_reset_code() -> str:
    """
    Generate a random alphanumeric code for password reset.

    Returns:
        A string of 6 uppercase letters and digits.
    """
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(constants.PASSWORD_RESET_CODE_SIZE))


def send_password_recovery_email(user: User, reset_code_uuid: str | UUID, reset_code: str) -> None:
    """
    Send password recovery email with the reset code to the user.

    Args:
        user: The user requesting password recovery.
        reset_code_uuid: The UUID of the password reset code.
        reset_code: The 6-character reset code.
    """
    # Import here to avoid circular import
    from apps.notifications.services import create_notification

    subject = "Recuperación de contraseña"
    message = (
        f"Tu código de recuperación es: {reset_code} y expira en "
        f"{settings.VERIFICATION_CODE_EXPIRATION_MINUTES} minutos. "
        f"UUID: {reset_code_uuid}"
    )
    create_notification(
        subject=subject,
        message=message,
        recipient_list=[user],
    )


def issue_password_reset_code(user: User) -> PasswordResetCode:
    """Create a reset code for the user and send the recovery email."""
    reset_code = generate_password_reset_code()
    expiration_date = timezone.now() + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRATION_MINUTES
    )
    password_reset_code = PasswordResetCode.objects.create(
        user=user, code=reset_code, expires_at=expiration_date
    )
    send_password_recovery_email(user, password_reset_code.id, password_reset_code.code)
    return password_reset_code


def request_password_recovery(email: str) -> None:
    """
    Request password recovery by generating and sending a reset code via email.

    For security reasons, this function always succeeds even if the email
    doesn't exist in the system, to prevent email enumeration attacks.

    Args:
        email: The email address of the user requesting password recovery.
    """
    try:
        user = User.objects.get(email=email, is_active=True, is_removed=False)
    except User.DoesNotExist:
        # Return silently to prevent email enumeration
        return

    issue_password_reset_code(user)


def request_admin_password_recovery(*, user_id: str | UUID, actor: User) -> None:
    """Staff-triggered password recovery for a specific user."""
    user = get_object_or_404(User, id=user_id, is_removed=False)
    assert_can_manage_admin_user(actor, user)

    if not (user.email or "").strip():
        raise ValueError(constants.PASSWORD_RECOVERY_ADMIN_MISSING_EMAIL_MESSAGE)
    if not user.is_active:
        raise ValueError(constants.PASSWORD_RECOVERY_ADMIN_INACTIVE_MESSAGE)

    issue_password_reset_code(user)


def confirm_password_reset(code: str, new_password: str) -> None:
    """
    Confirm password reset by validating the code and updating the user's password.

    Args:
        code: The 6-character reset code.
        new_password: The new password to set.

    Raises:
        PasswordResetCode.DoesNotExist: If the code is invalid or already used.
        ValueError: If the code has expired or the password is invalid.
    """
    now = timezone.now()

    try:
        reset_code = PasswordResetCode.objects.get(code=code, is_removed=False, expires_at__gt=now)
    except PasswordResetCode.DoesNotExist:
        raise ValueError(constants.PASSWORD_RECOVERY_INVALID_CODE_MESSAGE)

    # Check if code has expired
    if reset_code.expires_at <= now:
        reset_code.delete()  # Soft delete expired code
        raise ValueError(constants.PASSWORD_RECOVERY_CODE_EXPIRED_MESSAGE)

    # Validate new password
    try:
        validate_password(new_password, reset_code.user)
    except ValidationError as e:
        raise ValueError("; ".join(e.messages))

    # Update password
    reset_code.user.set_password(new_password)
    reset_code.user.save(update_fields=["password"])

    # Invalidate the code (soft delete)
    reset_code.delete()


def list_admin_users(*, search: str | None = None, role: str | None = None) -> list[dict]:
    """Return non-deleted users for the staff admin list."""
    queryset = User.objects.filter(is_removed=False).order_by("first_name", "last_name", "email")

    if role == "staff":
        queryset = queryset.filter(is_staff=True)
    elif role == "members":
        queryset = queryset.filter(is_staff=False)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(first_name__icontains=term)
            | Q(last_name__icontains=term)
            | Q(email__icontains=term)
            | Q(username__icontains=term)
            | Q(phone_number__icontains=term)
        )

    return [AdminUserSchema.model_validate(user).model_dump(mode="json") for user in queryset]


def pending_email_for(user: User) -> str | None:
    now = timezone.now()
    request = (
        EmailChangeRequest.objects.filter(user=user, is_removed=False, expires_at__gt=now)
        .order_by("-created")
        .first()
    )
    return request.new_email if request else None


def assert_email_available(email: str, *, exclude_user_id: str | UUID | None = None) -> str:
    normalized = (email or "").strip()
    if not normalized:
        raise ValueError("El correo electrónico es obligatorio.")
    queryset = User.objects.filter(is_removed=False).filter(
        Q(email__iexact=normalized) | Q(username__iexact=normalized)
    )
    if exclude_user_id is not None:
        queryset = queryset.exclude(id=exclude_user_id)
    if queryset.exists():
        raise ValueError(constants.EMAIL_CHANGE_TAKEN_MESSAGE)
    return normalized


def reject_immediate_email_change(data: dict, user: User) -> None:
    """Staff cannot apply a new email without the confirmation flow."""
    if "email" not in data:
        return
    incoming = (data.get("email") or "").strip()
    current = (user.email or "").strip()
    if incoming.lower() != current.lower():
        raise ValueError(constants.EMAIL_CHANGE_REQUIRES_CONFIRMATION_MESSAGE)
    data.pop("email", None)


def apply_confirmed_email(user: User, email: str) -> None:
    dirty_fields = ["email"]
    sync_username = bool(user.username) and user.username == (user.email or "")
    if sync_username:
        user.username = email
        dirty_fields.append("username")
    user.email = email
    user.save(update_fields=dirty_fields)


def _frontend_url() -> str:
    return (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip("/")


def send_email_change_email(
    user: User, new_email: str, change_uuid: str | UUID, change_code: str
) -> None:
    from apps.notifications.email_templates import render_email_change
    from apps.notifications.mailing import Email, mark_notification_as_sent
    from apps.notifications.models import Notification

    hours = getattr(settings, "EMAIL_VERIFICATION_EXPIRATION_HOURS", 24)
    frontend_url = _frontend_url()
    confirm_url = f"{frontend_url}/#confirm-email/{change_uuid}/{change_code}"
    subject = "Confirma tu nuevo correo en PulseFit"
    message = f"Confirma tu nuevo correo {new_email}: {confirm_url} " f"(caduca en {hours} horas)."
    html_content = render_email_change(
        new_email=new_email,
        confirm_url=confirm_url,
        frontend_url=frontend_url,
        hours=hours,
    )
    notification = Notification.objects.create(
        user=user,
        subject=subject,
        message=message,
        html_content=html_content,
    )
    Email(
        notification_id=str(notification.id),
        subject=subject,
        message=message,
        recipient_list=[new_email],
        html_content=html_content,
    ).send_mail()
    mark_notification_as_sent(str(notification.id))


def request_admin_email_change(*, user_id: str | UUID, email: str, actor: User) -> str:
    """Staff-triggered email change. The current email stays until the user confirms."""
    user = get_object_or_404(User, id=user_id, is_removed=False)
    assert_can_manage_admin_user(actor, user)

    new_email = assert_email_available(email, exclude_user_id=user.id)
    if new_email.lower() == (user.email or "").strip().lower():
        raise ValueError(constants.EMAIL_CHANGE_SAME_EMAIL_MESSAGE)

    EmailChangeRequest.objects.filter(user=user, is_removed=False).delete()
    change_request = EmailChangeRequest.objects.create(
        user=user,
        new_email=new_email,
        code=generate_password_reset_code(),
        expires_at=timezone.now()
        + timedelta(hours=getattr(settings, "EMAIL_VERIFICATION_EXPIRATION_HOURS", 24)),
    )
    send_email_change_email(user, new_email, change_request.id, change_request.code)
    return new_email


def confirm_email_change(change_uuid: str | UUID, code: str) -> None:
    now = timezone.now()
    try:
        change_request = EmailChangeRequest.objects.select_related("user").get(
            id=change_uuid,
            code=code,
            is_removed=False,
            expires_at__gt=now,
        )
    except EmailChangeRequest.DoesNotExist:
        raise ValueError(constants.EMAIL_CHANGE_INVALID_CODE_MESSAGE)

    new_email = assert_email_available(
        change_request.new_email, exclude_user_id=change_request.user_id
    )
    apply_confirmed_email(change_request.user, new_email)
    change_request.delete()


def assert_can_manage_admin_user(actor: User, user: User) -> None:
    if user.is_superuser and not actor.is_superuser:
        raise PermissionError("Solo un superuser puede editar a un superuser.")


def get_admin_user(*, user_id: str | UUID, actor: User) -> dict:
    """Return one non-deleted user for the staff admin."""
    user = get_object_or_404(User, id=user_id, is_removed=False)
    assert_can_manage_admin_user(actor, user)
    payload = AdminUserSchema.model_validate(user).model_dump(mode="json")
    payload["pending_email"] = pending_email_for(user)
    return payload


def update_admin_user(*, user_id: str | UUID, data: dict, actor: User) -> dict:
    """Update staff-editable user fields. Superuser flag is never changed here."""
    user = get_object_or_404(User, id=user_id, is_removed=False)
    assert_can_manage_admin_user(actor, user)
    allowed_fields = {
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "gender",
        "is_staff",
        "is_active",
    }
    gender_values = {"", "female", "male", "other"}

    if "gender" in data and data["gender"] is not None and data["gender"] not in gender_values:
        raise ValueError("Género inválido.")

    reject_immediate_email_change(data, user)

    if actor.id == user.id:
        if data.get("is_staff") is False:
            raise ValueError("No puedes quitarte el acceso staff a ti mismo.")
        if data.get("is_active") is False:
            raise ValueError("No puedes desactivar tu propia cuenta.")

    dirty_fields: list[str] = []

    for field, value in data.items():
        if field not in allowed_fields:
            continue
        if field in {"first_name", "last_name", "phone_number", "gender"} and value is None:
            value = ""
        setattr(user, field, value)
        dirty_fields.append(field)

    if dirty_fields:
        user.save(update_fields=list(dict.fromkeys(dirty_fields)))

    payload = AdminUserSchema.model_validate(user).model_dump(mode="json")
    payload["pending_email"] = pending_email_for(user)
    return payload
