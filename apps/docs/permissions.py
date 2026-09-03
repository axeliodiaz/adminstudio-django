"""Audience-level access policy for published documentation."""

from apps.docs.models import DocAudience

PUBLIC_DOC_AUDIENCES = frozenset(
    {
        DocAudience.MEMBER,
        DocAudience.PLATFORM,
    }
)


def allowed_doc_audiences(user) -> frozenset[str]:
    """Return exactly the documentation audiences visible to ``user``.

    Access is intentionally additive: a staff member who is also a coach may
    read both protected areas, while staff status alone does not grant coach
    documentation access (and vice versa).
    """
    audiences = set(PUBLIC_DOC_AUDIENCES)
    if not user or not user.is_authenticated:
        return frozenset(audiences)

    if user.is_staff:
        audiences.add(DocAudience.ADMIN)
    if user.is_coach:
        audiences.add(DocAudience.COACH)
    return frozenset(audiences)
