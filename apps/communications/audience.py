"""Audience filter engine for the Communications module (CYC-392).

A filter definition is JSON::

    {
        "group_operator": "or" | "and",        # how groups combine (default "or")
        "groups": [
            {
                "operator": "and" | "or",      # how conditions inside combine
                "conditions": [
                    {"type": "no_visit_in_days", "params": {"days": 30}},
                    ...
                ],
            }
        ],
    }

A flat shorthand ``{"operator": ..., "conditions": [...]}`` is accepted and
treated as a single group. Every audience excludes staff accounts and
unsubscribed people (see ``get_unsubscribed_user_ids``).
"""

import operator
from datetime import timedelta
from functools import reduce

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

User = get_user_model()

DEFAULT_SAMPLE_SIZE = 10
MAX_SAMPLE_SIZE = 25


class AudienceFilterError(ValueError):
    """Raised when an audience filter definition is invalid."""


def get_unsubscribed_user_ids():
    """Users excluded from every audience (opt-out).

    CYC-397 (unsubscribe storage and endpoint) is pending Axel's consent
    decision, so there is no unsubscribe list yet. This seam keeps the
    exclusion wired so audiences apply it the day the list exists.
    """
    return User.objects.none()


def _attended_user_ids_since(cutoff):
    from apps.members import constants as member_constants
    from apps.members.models import Reservation

    return Reservation.objects.filter(
        is_removed=False,
        status=member_constants.RESERVATION_STATUS_ATTENDED,
        schedule__start_time__gte=cutoff,
    ).values_list("member__user_id", flat=True)


def _q_no_visit_in_days(params):
    days = params["days"]
    cutoff = timezone.now() - timedelta(days=days)
    # Includes people who have never attended a class.
    return ~Q(id__in=_attended_user_ids_since(cutoff))


def _q_pack_expiring_in_days(params):
    from apps.wallets.models import PlanPurchase, Wallet

    days = params["days"]
    today = timezone.localdate()
    limit = today + timedelta(days=days)
    wallet_qs = Wallet.objects.filter(
        active_membership_end_date__gte=today,
        active_membership_end_date__lte=limit,
    ).values_list("user_id", flat=True)
    purchase_qs = PlanPurchase.objects.filter(
        end__isnull=False,
        end__date__gte=today,
        end__date__lte=limit,
    ).values_list("user_id", flat=True)
    return Q(id__in=wallet_qs) | Q(id__in=purchase_qs)


def _q_never_booked(params):
    from apps.members.models import Reservation

    booked = Reservation.objects.filter(is_removed=False).values_list("member__user_id", flat=True)
    return ~Q(id__in=booked)


def _q_has_class_credits(params):
    from apps.wallets.models import Wallet

    min_credits = params.get("min", 1)
    wallet_qs = Wallet.objects.filter(class_credits__gte=min_credits).values_list(
        "user_id", flat=True
    )
    return Q(id__in=wallet_qs)


def _require_days(params):
    days = params.get("days")
    if not isinstance(days, int) or isinstance(days, bool) or days < 1:
        raise AudienceFilterError("This condition requires an integer 'days' >= 1.")
    return days


def _optional_min_credits(params):
    min_credits = params.get("min", 1)
    if not isinstance(min_credits, int) or isinstance(min_credits, bool) or min_credits < 0:
        raise AudienceFilterError("Condition 'has_class_credits' accepts an integer 'min' >= 0.")
    return min_credits


CONDITIONS = {
    "no_visit_in_days": {
        "label": "No visit in N days",
        "description": "People whose last attended class is older than N days (or who never attended).",
        "params": [
            {"name": "days", "type": "integer", "min": 1, "required": True, "unit": "days"},
        ],
        "build": _q_no_visit_in_days,
        "validate": _require_days,
    },
    "pack_expiring_in_days": {
        "label": "Pack or membership expiring in N days",
        "description": "People with an active membership or purchased pack ending within the next N days.",
        "params": [
            {"name": "days", "type": "integer", "min": 1, "required": True, "unit": "days"},
        ],
        "build": _q_pack_expiring_in_days,
        "validate": _require_days,
    },
    "never_booked": {
        "label": "Never booked",
        "description": "People who have never made a reservation.",
        "params": [],
        "build": _q_never_booked,
        "validate": lambda params: None,
    },
    "has_class_credits": {
        "label": "Has class credits",
        "description": "People with at least 'min' class credits in their wallet (default 1).",
        "params": [
            {"name": "min", "type": "integer", "min": 0, "required": False, "default": 1},
        ],
        "build": _q_has_class_credits,
        "validate": _optional_min_credits,
    },
}

OPERATORS = ("and", "or")


def _validate_operator(value, field):
    if value not in OPERATORS:
        raise AudienceFilterError(f"'{field}' must be one of {OPERATORS}; got {value!r}.")
    return value


def validate_filter_definition(definition):
    """Validate and normalize a raw filter definition.

    Returns ``{"group_operator": str, "groups": [{"operator": str,
    "conditions": [{"type": str, "params": dict}]}]}``.
    """
    if not isinstance(definition, dict):
        raise AudienceFilterError("'filter' must be an object.")

    if "groups" in definition:
        group_operator = _validate_operator(
            definition.get("group_operator", "or"), "group_operator"
        )
        raw_groups = definition["groups"]
        if not isinstance(raw_groups, list) or not raw_groups:
            raise AudienceFilterError("'groups' must be a non-empty list.")
    elif "conditions" in definition:
        group_operator = "or"
        raw_groups = [
            {
                "operator": definition.get("operator", "and"),
                "conditions": definition["conditions"],
            }
        ]
    else:
        raise AudienceFilterError("'filter' needs 'groups' or 'conditions'.")

    groups = []
    for index, raw_group in enumerate(raw_groups):
        if not isinstance(raw_group, dict):
            raise AudienceFilterError(f"Group #{index + 1} must be an object.")
        group_op = _validate_operator(raw_group.get("operator", "and"), "operator")
        raw_conditions = raw_group.get("conditions")
        if not isinstance(raw_conditions, list) or not raw_conditions:
            raise AudienceFilterError(f"Group #{index + 1} needs a non-empty 'conditions' list.")
        conditions = []
        for cond in raw_conditions:
            if not isinstance(cond, dict) or "type" not in cond:
                raise AudienceFilterError("Each condition needs a 'type'.")
            cond_type = cond["type"]
            spec = CONDITIONS.get(cond_type)
            if spec is None:
                raise AudienceFilterError(
                    f"Unknown condition type {cond_type!r}. " f"Available: {sorted(CONDITIONS)}."
                )
            params = cond.get("params") or {}
            if not isinstance(params, dict):
                raise AudienceFilterError(f"'params' of '{cond_type}' must be an object.")
            unknown_params = set(params) - {p["name"] for p in spec["params"]}
            if unknown_params:
                raise AudienceFilterError(
                    f"Unknown params for '{cond_type}': {sorted(unknown_params)}."
                )
            spec["validate"](params)
            conditions.append({"type": cond_type, "params": params})
        groups.append({"operator": group_op, "conditions": conditions})

    return {"group_operator": group_operator, "groups": groups}


def build_audience_queryset(definition):
    """Return the User queryset matching a validated filter definition."""
    normalized = validate_filter_definition(definition)

    group_qs = []
    for group in normalized["groups"]:
        condition_qs = [
            CONDITIONS[cond["type"]]["build"](cond["params"]) for cond in group["conditions"]
        ]
        combine = operator.and_ if group["operator"] == "and" else operator.or_
        group_qs.append(reduce(combine, condition_qs))

    combine_groups = operator.and_ if normalized["group_operator"] == "and" else operator.or_
    combined = reduce(combine_groups, group_qs)

    # Audiences are clients: active, non-staff users with an email address.
    base = (
        User.objects.filter(is_removed=False, is_active=True)
        .exclude(email__exact="")
        .exclude(is_staff=True)
        .exclude(is_superuser=True)
        .exclude(id__in=get_unsubscribed_user_ids())
    )
    return base.filter(combined)


def sample_audience(queryset, sample_size):
    """Return a stable sample of the audience for the preview list."""
    size = max(1, min(int(sample_size or DEFAULT_SAMPLE_SIZE), MAX_SAMPLE_SIZE))
    rows = queryset.order_by("email").values("id", "first_name", "last_name", "email")[:size]
    return [
        {
            "id": str(row["id"]),
            "name": (f"{row['first_name']} {row['last_name']}".strip() or row["email"]),
            "email": row["email"],
        }
        for row in rows
    ]
