"""People module views (CYC-399).

Admin-only module shell plus the unified member list: coaches, staff and
other members of the studio in one place. This is the base for the rest of
the People module (pay config, contracts, pay summaries).
"""

from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import paginate
from apps.instructors.models import Instructor
from apps.people.permissions import IsPeopleAdmin
from apps.users.models import User

ROLE_COACH = "coach"
ROLE_STAFF = "staff"
ROLE_MEMBER = "member"


def _coach_user_ids() -> set:
    return set(Instructor.objects.filter(is_removed=False).values_list("user_id", flat=True))


def _user_roles(user, coach_ids: set) -> list[str]:
    roles = []
    if user.is_staff or user.is_superuser:
        roles.append(ROLE_STAFF)
    if user.id in coach_ids:
        roles.append(ROLE_COACH)
    if not roles:
        roles.append(ROLE_MEMBER)
    return roles


class PeopleModuleView(APIView):
    """Module shell (CYC-399): confirms the People module exists.

    Feature flags advertise which sub-capabilities are wired so the
    frontend renders only what exists while later tickets land.
    """

    permission_classes = [IsAuthenticated, IsPeopleAdmin]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "module": "people",
                "status": "active",
                "features": {
                    "member_list": True,
                    "pay_configuration": False,
                    "contracts": False,
                    "pay_summaries": False,
                },
            }
        )


class PeopleMemberListView(APIView):
    """Unified list of coaches, staff and other members (CYC-399).

    Query params:
      - ``role``: coach | staff | member (``member`` means no staff/coach
        role; a user can be both coach and staff).
      - ``search``: case-insensitive match on name, username or email.
      - ``page`` / ``page_size``: standard pagination envelope.
    """

    permission_classes = [IsAuthenticated, IsPeopleAdmin]

    def get(self, request, *args, **kwargs):
        users = User.objects.filter(is_removed=False).order_by(
            "first_name", "last_name", "username"
        )
        search = (request.query_params.get("search") or "").strip()
        if search:
            users = users.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(username__icontains=search)
                | Q(email__icontains=search)
            )
        coach_ids = _coach_user_ids()
        role = (request.query_params.get("role") or "").strip().lower()
        if role == ROLE_STAFF:
            users = users.filter(Q(is_staff=True) | Q(is_superuser=True))
        elif role == ROLE_COACH:
            users = users.filter(id__in=coach_ids)
        elif role == ROLE_MEMBER:
            users = users.filter(is_staff=False, is_superuser=False).exclude(id__in=coach_ids)

        def serialize(user) -> dict:
            full_name = f"{user.first_name} {user.last_name}".strip()
            return {
                "id": str(user.id),
                "name": full_name or user.username,
                "email": user.email,
                "roles": _user_roles(user, coach_ids),
                "is_active": user.is_active,
                "date_joined": user.date_joined.isoformat(),
            }

        return Response(
            paginate(request.query_params, users, serialize),
            status=status.HTTP_200_OK,
        )
