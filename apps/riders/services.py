import pdb

from django.contrib.auth import get_user_model

from apps.riders.models import Rider
from apps.users.services import create_user
from apps.verifications.services import create_verification_code

User = get_user_model()


def get_or_create_user(data: dict) -> User:
    try:
        user = User.objects.get(email=data["email"])
    except User.DoesNotExist:
        user = create_user(data)
    return user


def get_or_create_rider_user(validated_data: dict) -> tuple[Rider, bool]:
    user = get_or_create_user(validated_data)
    created = False
    try:
        rider = Rider.objects.get(user=user)
    except Rider.DoesNotExist:
        rider = Rider.objects.create(user=user)
        created = True
        create_verification_code(user=rider.user)
    return rider, created
