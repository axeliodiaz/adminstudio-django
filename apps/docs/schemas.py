import uuid
from datetime import datetime

from pydantic import BaseModel


class DocPageSummarySchema(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    summary: str
    order: int
    related_app_route: str

    model_config = {"from_attributes": True}


class DocSectionPublicSchema(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    audience: str
    order: int
    pages: list[DocPageSummarySchema]


class DocAudienceGroupSchema(BaseModel):
    id: str
    label: str
    sections: list[DocSectionPublicSchema]


class DocsIndexSchema(BaseModel):
    audiences: list[DocAudienceGroupSchema]


class DocSectionRefSchema(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    audience: str


class DocPageDetailSchema(BaseModel):
    id: uuid.UUID
    title: str
    slug: str
    summary: str
    body: str
    order: int
    related_app_route: str
    modified: datetime
    section: DocSectionRefSchema
