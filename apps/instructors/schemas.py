import uuid
from datetime import datetime, date
from typing import Optional, Any

from pydantic import BaseModel, Field, field_serializer

from apps.users.schemas import UserSchema, UserPublicSchema


class InstructorSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    user: UserSchema

    # Optional profile information
    profile_image: Any | None = None
    description: str = ""
    tagline: str = ""

    # Social and contact
    website_url: str = ""
    instagram_username: str = ""
    tiktok_username: str = ""

    # Professional metadata
    is_verified: bool = False
    instructor_since: Optional[date] = None
    location: str = ""

    # Last playlist used per platform
    last_spotify_playlist: str = ""
    last_apple_music_playlist: str = ""
    last_youtube_music_playlist: str = ""

    model_config = {"from_attributes": True}

    @field_serializer("profile_image", when_used="always")
    def serialize_profile_image(self, value):
        try:
            if value and getattr(value, "name", ""):
                return value.url
        except Exception:
            return None
        return None


class InstructorPublicSchema(BaseModel):
    id: uuid.UUID
    created: datetime
    modified: datetime
    user: UserPublicSchema

    # Optional profile information
    profile_image: Any | None = None
    description: str = ""
    tagline: str = ""

    # Social and contact
    website_url: str = ""
    instagram_username: str = ""
    tiktok_username: str = ""

    # Professional metadata
    is_verified: bool = False
    instructor_since: Optional[date] = None
    location: str = ""

    # Last playlist used per platform
    last_spotify_playlist: str = ""
    last_apple_music_playlist: str = ""
    last_youtube_music_playlist: str = ""

    model_config = {"from_attributes": True}

    @field_serializer("profile_image", when_used="always")
    def serialize_profile_image(self, value):
        try:
            if value and getattr(value, "name", ""):
                return value.url
        except Exception:
            return None
        return None
