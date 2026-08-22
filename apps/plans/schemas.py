import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class BenefitSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class PlanSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    type: str
    price: float
    duration_days: int | None = None
    classes_included: int | None = None
    guest_passes_included: int | None = None
    is_active: bool
    is_popular: bool
    is_highlighted: bool
    # Public list exposes only active benefits via the model property
    benefits: list[BenefitSchema] | None = Field(default=None, alias="benefits_list")

    model_config = {"from_attributes": True}


class AdminPlanSchema(BaseModel):
    """Plan row for the staff admin list and detail (includes inactive benefits)."""

    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    type: str
    price: float
    duration_days: int | None = None
    classes_included: int | None = None
    guest_passes_included: int | None = None
    is_active: bool
    is_popular: bool
    is_highlighted: bool
    benefits: list[BenefitSchema] = Field(default_factory=list)
    benefit_ids: list[uuid.UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class AdminPlanWriteSchema(BaseModel):
    """Payload for creating or updating a plan from the staff admin."""

    name: str | None = None
    type: Literal["MEMBERSHIP", "PACKAGE"] | None = None
    price: float | None = None
    duration_days: int | None = None
    classes_included: int | None = None
    guest_passes_included: int | None = None
    is_active: bool | None = None
    is_popular: bool | None = None
    is_highlighted: bool | None = None
    benefit_ids: list[uuid.UUID] | None = None


class AdminBenefitSchema(BaseModel):
    """Benefit option for the staff admin plan editor."""

    id: uuid.UUID
    name: str
    description: str
    is_active: bool

    model_config = {"from_attributes": True}


class PromoCodeSchema(BaseModel):
    """Public validation result for a promotional code."""

    id: uuid.UUID
    code: str
    description: str = ""
    is_active: bool
    valid_from: datetime
    valid_until: datetime
    discount_type: str
    discount_value: float
    discount_amount: float | None = None
    subtotal: float | None = None
    total: float | None = None

    model_config = {"from_attributes": True}


class AdminPromoCodeSchema(BaseModel):
    """Promo code row for the staff admin."""

    id: uuid.UUID
    created: datetime
    modified: datetime
    code: str
    description: str = ""
    is_active: bool
    valid_from: datetime
    valid_until: datetime
    discount_type: str
    discount_value: float

    model_config = {"from_attributes": True}


class AdminPromoCodeWriteSchema(BaseModel):
    """Payload for creating or updating a promo code from the staff admin."""

    code: str | None = None
    description: str | None = None
    is_active: bool | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    discount_type: Literal["PERCENT", "FIXED"] | None = None
    discount_value: float | None = None
