from rest_framework.permissions import BasePermission


class IsInventoryAdmin(BasePermission):
    """Access gate for the Inventory module: admins only (Django ``is_superuser``).

    Plain staff, coaches and members get 403. Dedicated class so the module
    can be tightened in a single place.
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_superuser)
