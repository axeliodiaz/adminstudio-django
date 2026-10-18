"""Audience filter engine and endpoints (CYC-392)."""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from drf_expiring_token.models import ExpiringToken
from model_bakery import baker

from apps.communications import audience
from apps.communications.audience import AudienceFilterError
from apps.members import constants as member_constants

User = get_user_model()


def make_user(username, **kwargs):
    defaults = {"email": f"{username}@example.com", "password": "testpass123"}
    defaults.update(kwargs)
    return User.objects.create_user(username=username, **defaults)


@pytest.fixture
def staff_client(api_client):
    staff = make_user("audience.admin", is_staff=True)
    token = ExpiringToken.objects.create(user=staff)
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return api_client


@pytest.mark.django_db
class TestValidateFilterDefinition:
    def test_rejects_unknown_condition_type(self):
        with pytest.raises(AudienceFilterError, match="Unknown condition type"):
            audience.validate_filter_definition(
                {"operator": "and", "conditions": [{"type": "magic"}]}
            )

    def test_rejects_missing_days(self):
        with pytest.raises(AudienceFilterError, match="days"):
            audience.validate_filter_definition(
                {"operator": "and", "conditions": [{"type": "no_visit_in_days"}]}
            )

    def test_rejects_invalid_operator(self):
        with pytest.raises(AudienceFilterError, match="operator"):
            audience.validate_filter_definition(
                {"operator": "xor", "conditions": [{"type": "never_booked"}]}
            )

    def test_rejects_unknown_params(self):
        with pytest.raises(AudienceFilterError, match="Unknown params"):
            audience.validate_filter_definition(
                {
                    "operator": "and",
                    "conditions": [{"type": "never_booked", "params": {"days": 3}}],
                }
            )

    def test_flat_shorthand_becomes_single_group(self):
        normalized = audience.validate_filter_definition(
            {"operator": "or", "conditions": [{"type": "never_booked"}]}
        )
        assert normalized["group_operator"] == "or"
        assert len(normalized["groups"]) == 1
        assert normalized["groups"][0]["operator"] == "or"

    def test_groups_definition_is_normalized(self):
        normalized = audience.validate_filter_definition(
            {
                "group_operator": "and",
                "groups": [
                    {
                        "operator": "or",
                        "conditions": [
                            {"type": "never_booked"},
                            {"type": "no_visit_in_days", "params": {"days": 15}},
                        ],
                    }
                ],
            }
        )
        assert normalized["group_operator"] == "and"
        assert normalized["groups"][0]["conditions"][1]["params"] == {"days": 15}


@pytest.mark.django_db
class TestBuildAudienceQueryset:
    def test_never_booked(self):
        fresh = make_user("fresh")
        regular = make_user("regular")
        reservation = baker.make(
            "members.Reservation", member=baker.make("members.Member", user=regular)
        )
        assert reservation.pk
        qs = audience.build_audience_queryset({"conditions": [{"type": "never_booked"}]})
        assert fresh in qs
        assert regular not in qs

    def test_no_visit_in_days_includes_stale_and_never_attended(self):
        never = make_user("never")
        recent = make_user("recent")
        stale = make_user("stale")
        now = timezone.now()
        for user, days_ago in ((recent, 2), (stale, 40)):
            member = baker.make("members.Member", user=user)
            schedule = baker.make("schedules.Schedule", start_time=now - timedelta(days=days_ago))
            baker.make(
                "members.Reservation",
                member=member,
                schedule=schedule,
                status=member_constants.RESERVATION_STATUS_ATTENDED,
            )
        qs = audience.build_audience_queryset(
            {"conditions": [{"type": "no_visit_in_days", "params": {"days": 30}}]}
        )
        assert never in qs
        assert stale in qs
        assert recent not in qs

    def test_pack_expiring_in_days(self):
        expiring = make_user("expiring")
        safe = make_user("safe")
        today = timezone.localdate()
        baker.make(
            "wallets.Wallet",
            user=expiring,
            active_membership_end_date=today + timedelta(days=5),
        )
        baker.make(
            "wallets.Wallet",
            user=safe,
            active_membership_end_date=today + timedelta(days=60),
        )
        qs = audience.build_audience_queryset(
            {"conditions": [{"type": "pack_expiring_in_days", "params": {"days": 10}}]}
        )
        assert expiring in qs
        assert safe not in qs

    def test_has_class_credits(self):
        rich = make_user("rich")
        broke = make_user("broke")
        baker.make("wallets.Wallet", user=rich, class_credits=4)
        baker.make("wallets.Wallet", user=broke, class_credits=0)
        qs = audience.build_audience_queryset(
            {"conditions": [{"type": "has_class_credits", "params": {"min": 2}}]}
        )
        assert rich in qs
        assert broke not in qs

    def test_and_or_combination(self):
        never_with_credits = make_user("never_with_credits")
        never_without_credits = make_user("never_without_credits")
        baker.make("wallets.Wallet", user=never_with_credits, class_credits=3)
        baker.make("wallets.Wallet", user=never_without_credits, class_credits=0)
        qs = audience.build_audience_queryset(
            {
                "operator": "and",
                "conditions": [
                    {"type": "never_booked"},
                    {"type": "has_class_credits", "params": {"min": 1}},
                ],
            }
        )
        assert never_with_credits in qs
        assert never_without_credits not in qs

    def test_staff_and_superusers_are_excluded(self):
        staff = make_user("staff.audience", is_staff=True)
        superuser = make_user("super.audience", is_superuser=True)
        member = make_user("plain.audience")
        qs = audience.build_audience_queryset({"conditions": [{"type": "never_booked"}]})
        assert member in qs
        assert staff not in qs
        assert superuser not in qs

    def test_users_without_email_are_excluded(self):
        no_email = make_user("noemail", email="")
        qs = audience.build_audience_queryset({"conditions": [{"type": "never_booked"}]})
        assert no_email not in qs


@pytest.mark.django_db
class TestAudienceEndpoints:
    def test_conditions_require_staff(self, api_client):
        response = api_client.get(reverse("communications-audience-conditions"))
        assert response.status_code == 401

    def test_conditions_list_for_staff(self, staff_client):
        response = staff_client.get(reverse("communications-audience-conditions"))
        assert response.status_code == 200
        types = {c["type"] for c in response.json()["conditions"]}
        assert {"no_visit_in_days", "pack_expiring_in_days", "never_booked"} <= types

    def test_preview_returns_count_and_sample(self, staff_client):
        for index in range(3):
            make_user(f"sample{index}")
        response = staff_client.post(
            reverse("communications-audience-preview"),
            {"filter": {"conditions": [{"type": "never_booked"}]}, "sample_size": 2},
            format="json",
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["count"] == 3
        assert len(payload["sample"]) == 2
        assert payload["sample"][0]["email"].endswith("@example.com")

    def test_preview_rejects_invalid_filter(self, staff_client):
        response = staff_client.post(
            reverse("communications-audience-preview"),
            {"filter": {"conditions": [{"type": "magic"}]}},
            format="json",
        )
        assert response.status_code == 400
        assert "Unknown condition type" in response.json()["detail"]

    def test_preview_requires_filter(self, staff_client):
        response = staff_client.post(reverse("communications-audience-preview"), {}, format="json")
        assert response.status_code == 400

    def test_preview_forbidden_for_members(self, api_client):
        member = make_user("member.audience")
        token = ExpiringToken.objects.create(user=member)
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        response = api_client.post(
            reverse("communications-audience-preview"),
            {"filter": {"conditions": [{"type": "never_booked"}]}},
            format="json",
        )
        assert response.status_code == 403
