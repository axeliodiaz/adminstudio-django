from apps.members import members
from apps.members.schemas import MemberSchema


def get_or_create_member_user(validated_data: dict) -> tuple[MemberSchema, bool]:
    """
    Application service: delegates to domain logic (apps.members.members)
    and returns a Pydantic MemberSchema along with the created flag.
    """
    member, created = members.get_or_create_member_user(validated_data)
    return MemberSchema.model_validate(member), created
