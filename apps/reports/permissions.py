from rest_framework.permissions import BasePermission


class IsReportsAdmin(BasePermission):
    """Access gate for the Reports module: admins only (Django ``is_superuser``).

    Plain staff, coaches and members get 403. Dedicated class so the module
    can be tightened in a single place (studio-scoped admins, CYC-433).
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)
