import pytest
from django.contrib.auth import get_user_model

from apps.instructors.axel_diaz_coach import ensure_axel_diaz_is_coach, find_axel_diaz_user
from apps.instructors.models import Instructor

User = get_user_model()


@pytest.mark.django_db
class TestEnsureAxelDiazIsCoach:
    def test_matches_name_with_accent_and_does_not_create_user(self):
        user = User.objects.create_user(
            username="axeldiaz",
            email="axel.diaz@pulsefit.cl",
            first_name="Axel",
            last_name="Díaz",
            password="secret",
        )
        User.objects.create_user(username="other", email="other@example.com", password="secret")

        instructor = ensure_axel_diaz_is_coach(User, Instructor)

        assert instructor is not None
        assert instructor.user_id == user.pk
        assert user.check_password("secret")
        assert find_axel_diaz_user(User).pk == user.pk
        assert User.objects.filter(username="axelio").exists() is False

    def test_returns_none_when_user_missing(self):
        assert ensure_axel_diaz_is_coach(User, Instructor) is None
