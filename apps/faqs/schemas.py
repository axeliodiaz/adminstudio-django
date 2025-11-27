import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from apps.faqs.models import Section, FAQItem


class SectionSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    name: str
    slug: str
    description: str
    order: int

    model_config = {"from_attributes": True}


class FAQItemSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    section: SectionSchema
    question: str
    answer: str  # Markdown content
    order: int
    is_published: bool

    model_config = {"from_attributes": True}


class FAQPublicSchema(BaseModel):
    """Schema for public FAQ endpoint - grouped by sections."""

    sections: list[dict]

    model_config = {"from_attributes": False}
