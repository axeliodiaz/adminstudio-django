import random
import string
from datetime import datetime, timedelta, timezone
from uuid import UUID

from django.conf import settings

from apps.notifications.email_templates import render_verify_email, render_welcome_email
from apps.notifications.services import create_notification
from apps.verifications import constants
from apps.verifications.models import VerificationCode


def _frontend_url() -> str:
    return (getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173").rstrip("/")


def validate_code(validation_code: VerificationCode) -> VerificationCode:
    user = validation_code.user
    user.is_active = True
    user.save(update_fields=["is_active"])
    # Invalidate the code (soft delete)
    validation_code.delete()
    send_welcome_email(user)
    return validation_code


def send_welcome_email(user: "users.User") -> None:
    first_name = (user.first_name or "").strip()
    frontend_url = _frontend_url()
    classes_url = f"{frontend_url}/#classes"
    subject = f"Bienvenida a PulseFit, {first_name}" if first_name else "Bienvenida a PulseFit"
    message = (
        f"Hola {first_name or 'rider'}, tu cuenta en PulseFit Studio ya está activa. "
        f"Reserva tu primera clase: {classes_url}"
    )
    create_notification(
        subject=subject,
        message=message,
        recipient_list=[user],
        html_content=render_welcome_email(
            first_name=first_name,
            classes_url=classes_url,
            frontend_url=frontend_url,
        ),
    )


def send_email_verification(
    user: "users.User", verification_uuid: str | UUID, verification_code: str
):
    hours = getattr(settings, "EMAIL_VERIFICATION_EXPIRATION_HOURS", 24)
    frontend_url = _frontend_url()
    verify_url = f"{frontend_url}/#verify/{verification_uuid}/{verification_code}"
    subject_email_verification = "Confirma tu correo en PulseFit"
    message_email_verification = (
        f"Confirma tu correo para activar tu cuenta: {verify_url} " f"(caduca en {hours} horas)."
    )
    create_notification(
        subject=subject_email_verification,
        message=message_email_verification,
        recipient_list=[user],
        html_content=render_verify_email(
            email=user.email or "",
            verify_url=verify_url,
            frontend_url=frontend_url,
            hours=hours,
        ),
    )


def generate_verification_code():
    chars = string.ascii_uppercase + string.digits
    random_code = "".join(random.choice(chars) for _ in range(constants.VERIFICATION_CODE_SIZE))
    return random_code


def create_verification_code(user: "users.User") -> VerificationCode:
    random_code = generate_verification_code()
    expiration_date = datetime.now(timezone.utc) + timedelta(
        hours=getattr(settings, "EMAIL_VERIFICATION_EXPIRATION_HOURS", 24)
    )
    verification_code = VerificationCode.objects.create(
        user=user, code=random_code, expires_at=expiration_date
    )
    send_email_verification(user, verification_code.id, verification_code.code)
    return verification_code
