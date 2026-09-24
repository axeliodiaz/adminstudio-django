from datetime import timedelta

import pytest
from django.utils import timezone
from model_bakery import baker


@pytest.fixture
def inactive_user():
    return baker.make("users.User", is_active=False)


@pytest.fixture
def verification_code(inactive_user):
    return baker.make(
        "verifications.VerificationCode",
        user=inactive_user,
        has_confirmed=False,
        expires_at=timezone.now() + timedelta(hours=1),
    )
