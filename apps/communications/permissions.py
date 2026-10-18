from rest_framework.permissions import IsAdminUser


class IsCommunicationsAdmin(IsAdminUser):
    """Access gate for the Communications module.

    Same gate as the rest of the staff admin panel (Django ``is_staff``).
    Kept as a dedicated class so the module can be tightened (for example
    to superusers only) in a single place if that decision is made.
    """
