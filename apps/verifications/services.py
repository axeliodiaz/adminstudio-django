import random
import string
from datetime import datetime, timedelta, timezone

from django.conf import settings

from apps.notifications.services import create_notification
from apps.verifications import constants
from apps.verifications.models import VerificationCode


def validate_code(validation_code: VerificationCode) -> VerificationCode:
    validation_code.user.is_active = True
    validation_code.user.save(update_fields=["is_active"])
    # Invalidate the code (soft delete)
    validation_code.delete()
    return validation_code


def send_email_verification(user: "users.User", verification_code: str):
    subject_email_verification = "Please confirm your subscription"
    message_email_verification = (
        f"Your verification code is: {verification_code} and expires in "
        f"{settings.VERIFICATION_CODE_EXPIRATION_MINUTES} minutes."
    )
    create_notification(
        subject=subject_email_verification,
        message=message_email_verification,
        recipient_list=[user],
    )


def generate_verification_code():
    chars = string.ascii_uppercase + string.digits
    random_code = "".join(random.choice(chars) for _ in range(constants.VERIFICATION_CODE_SIZE))
    return random_code


def create_verification_code(user: "users.User") -> VerificationCode:
    random_code = generate_verification_code()
    expiration_date = datetime.now(timezone.utc) + timedelta(
        minutes=settings.VERIFICATION_CODE_EXPIRATION_MINUTES
    )
    verification_code = VerificationCode.objects.create(
        user=user, code=random_code, expires_at=expiration_date
    )
    send_email_verification(user, verification_code.code)
    return verification_code
