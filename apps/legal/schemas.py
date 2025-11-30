import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from apps.legal.models import LegalDocument


class LegalDocumentSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    document_type: str
    title: str
    slug: str
    content: str  # Markdown content
    language: str
    version: str
    effective_date: date
    is_published: bool
    order: int

    model_config = {"from_attributes": True}


class LegalDocumentPublicSchema(BaseModel):
    """Schema for public legal document endpoint."""

    id: uuid.UUID
    document_type: str
    title: str
    slug: str
    content: str  # Markdown content
    language: str
    version: str
    effective_date: date
    last_updated: datetime

    model_config = {"from_attributes": True}
