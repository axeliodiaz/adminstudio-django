import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class WalletSchema(BaseModel):
    """Schema for Wallet model."""

    id: uuid.UUID
    created: datetime
    modified: datetime
    class_credits: int
    guest_pass_credits: int
    active_membership_end_date: date | None = None
    retail_discount_percentage: Decimal
    is_priority_booker: bool
    can_freeze_membership: bool
    is_founders_exclusive: bool
    is_unlimited_membership_active: bool

    model_config = {"from_attributes": True}


class PlanPurchaseSchema(BaseModel):
    """Schema for PlanPurchase model."""

    id: uuid.UUID
    created: datetime
    modified: datetime
    price_paid: Decimal
    activated_since: date | None = None
    start: datetime | None = None
    end: datetime | None = None
    plan_id: uuid.UUID
    plan_name: str | None = None

    model_config = {"from_attributes": True}


class WalletDashboardSchema(BaseModel):
    """Schema for wallet dashboard response."""

    wallet: WalletSchema
    purchases: list[PlanPurchaseSchema]

    model_config = {"from_attributes": True}
