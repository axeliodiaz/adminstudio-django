from apps.members.models import Member
from apps.users.services import get_or_create_user
from apps.verifications.services import create_verification_code


def get_or_create_member_user(validated_data: dict) -> tuple[Member, bool]:
    """
    Gets or creates a member user record based on the provided validated data.

    This function first attempts to get or create a user object using the
    validated data. Subsequently, it retrieves or creates a member member record
    corresponding to the user. If the member record is newly created, a
    verification code is generated for the associated user.

    Parameters:
        validated_data (dict): A dictionary containing the user-related data
                               necessary to create or find the user record.

    Returns:
        tuple[Member, bool]: A tuple containing the member member object and a
                             boolean indicating whether the member record was
                             created (True) or retrieved (False).
    """
    user = get_or_create_user(validated_data)
    member, created = Member.objects.get_or_create(user=user)
    if created:
        create_verification_code(user=member.user)
    return member, created
