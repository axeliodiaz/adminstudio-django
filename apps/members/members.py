from apps.members.models import Member
from apps.users.services import get_or_create_user
from apps.verifications.services import create_verification_code


def get_or_create_member_user(validated_data: dict) -> tuple[Member, bool]:
    """
    Domain logic for members: get or create Member linked to a User.

    Returns a tuple of (Member instance, created flag).
    """
    user = get_or_create_user(validated_data)
    member, created = Member.objects.get_or_create(user=user)
    if created:
        create_verification_code(user=member.user)
    return member, created
