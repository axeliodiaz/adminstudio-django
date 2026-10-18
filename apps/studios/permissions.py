from rest_framework.permissions import BasePermission


class IsBrandingAdmin(BasePermission):
    """Single access policy for editing studio branding.

    Today only Django superusers may edit. When studio-level admins exist, change
    ``can_edit_branding`` here (it receives the target studio, or None for the
    default branding) and every branding endpoint follows.
    """

    @staticmethod
    def can_edit_branding(user, studio=None) -> bool:
        return bool(user and user.is_authenticated and user.is_superuser)

    def has_permission(self, request, view):
        studio_id = request.query_params.get("studio") or None
        studio = None
        if studio_id:
            from apps.studios.models import Studio

            try:
                studio = Studio.objects.filter(pk=studio_id).first()
            except (ValueError, TypeError):
                studio = None
            except Exception:  # malformed uuid etc: policy is decided on the user
                studio = None
        return self.can_edit_branding(request.user, studio)
