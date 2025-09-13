from django.contrib.auth import get_user_model

from apps.riders.models import Rider
from apps.users.services import create_user

User = get_user_model()


def get_or_create_user(data: dict) -> User:
    try:
        user = User.objects.get(email=data["email"])
    except User.DoesNotExist:
        user = create_user(data)
    return user


def create_rider_user(validated_data: dict) -> Rider:
    user = get_or_create_user(validated_data)
    try:
        rider = Rider.objects.get(user=user)
    except Rider.DoesNotExist:
        rider = Rider.objects.create(user=user)
    return rider
