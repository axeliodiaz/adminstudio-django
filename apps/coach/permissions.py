from rest_framework.permissions import BasePermission

from apps.coach.constants import NOT_COACH_DETAIL
from apps.instructors.models import Instructor


class IsCoach(BasePermission):
    """Authenticated user with a non-removed Instructor profile."""

    message = NOT_COACH_DETAIL

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return Instructor.objects.filter(user_id=user.pk, is_removed=False).exists()
