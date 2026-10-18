from rest_framework.permissions import IsAdminUser


class IsPeopleAdmin(IsAdminUser):
    """Access gate for the People module.

    Same gate as the rest of the staff admin panel (Django ``is_staff``).
    Dedicated class so the module can be tightened in a single place.
    """
