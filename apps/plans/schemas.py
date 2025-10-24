import uuid
from datetime import datetime

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
    is_active: bool
    is_popular: bool
    is_highlighted: bool
    # If later a property like `benefits_list` is added to the model, we can expose it via alias
    benefits: list[BenefitSchema] | None = Field(default=None, alias="benefits_list")

    model_config = {"from_attributes": True}
