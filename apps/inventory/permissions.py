from rest_framework.permissions import IsAdminUser


class IsInventoryAdmin(IsAdminUser):
    """Access gate for the Inventory module.

    Same gate as the rest of the staff admin panel (Django ``is_staff``).
    Dedicated class so the module can be tightened in a single place.
    """
