"""Dashboard analytics constants."""

from apps.members.constants import (
    RESERVATION_STATUS_ATTENDED,
    RESERVATION_STATUS_MISSED,
    RESERVATION_STATUS_RESERVED,
)
from apps.schedules.constants import (
    SCHEDULE_STATUS_CANCELED,
    SCHEDULE_STATUS_DRAFT,
)

# Spots that counted toward occupancy (the member held a bike).
OCCUPIED_RESERVATION_STATUSES = (
    RESERVATION_STATUS_RESERVED,
    RESERVATION_STATUS_ATTENDED,
    RESERVATION_STATUS_MISSED,
)

EXCLUDED_SCHEDULE_STATUSES = (
    SCHEDULE_STATUS_DRAFT,
    SCHEDULE_STATUS_CANCELED,
)

CLASS_FORMATS = ("RIDE", "POWER", "YOGA", "SCULPT", "REFORMER")

# Fixed FX used to present the same 7d revenue in CLP / USD / MXN.
# Source of truth is always CLP (PlanPurchase.price_paid).
CLP_PER_USD = 950.0
CLP_PER_MXN = 52.5

DEMO_USERNAME_PREFIX = "demo.dash."
DEMO_EMAIL_DOMAIN = "pulsefit.demo"
DEMO_PLAN_PREFIX = "Demo · "
