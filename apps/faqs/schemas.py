import uuid
from datetime import datetime

from pydantic import BaseModel


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


class AdminSectionSchema(BaseModel):
    """FAQ section row for the PulseFit staff admin."""

    id: uuid.UUID
    name: str
    slug: str
    description: str
    order: int
    faq_count: int = 0
    created: datetime
    modified: datetime

    model_config = {"from_attributes": True}


class AdminSectionWriteSchema(BaseModel):
    """Payload for creating or updating an FAQ section."""

    name: str | None = None
    slug: str | None = None
    description: str | None = None
    order: int | None = None


class AdminFAQItemSchema(BaseModel):
    """FAQ item row for the PulseFit staff admin."""

    id: uuid.UUID
    section_id: uuid.UUID
    section_name: str
    question: str
    answer: str
    order: int
    is_published: bool
    created: datetime
    modified: datetime

    model_config = {"from_attributes": True}


class AdminFAQItemWriteSchema(BaseModel):
    """Payload for creating or updating an FAQ item."""

    section_id: uuid.UUID | None = None
    question: str | None = None
    answer: str | None = None
    order: int | None = None
    is_published: bool | None = None
