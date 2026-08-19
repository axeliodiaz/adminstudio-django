import uuid
from datetime import datetime, date
from typing import Optional, Any

from pydantic import BaseModel, EmailStr, field_serializer

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


def _profile_image_url(value) -> str | None:
    try:
        if value and getattr(value, "name", ""):
            return value.url
    except Exception:
        return None
    return None


class AdminInstructorSchema(BaseModel):
    """Flattened instructor row for the PulseFit staff admin."""

    id: uuid.UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone_number: str | None = None
    username: str | None = None
    description: str = ""
    tagline: str = ""
    website_url: str = ""
    instagram_username: str = ""
    tiktok_username: str = ""
    is_verified: bool = False
    instructor_since: Optional[date] = None
    location: str = ""
    last_spotify_playlist: str = ""
    last_apple_music_playlist: str = ""
    last_youtube_music_playlist: str = ""
    profile_image: str | None = None
    is_active: bool = True
    created: datetime
    modified: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_instructor(cls, instructor) -> "AdminInstructorSchema":
        user = instructor.user
        return cls(
            id=instructor.id,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            phone_number=getattr(user, "phone_number", None),
            username=user.username,
            description=instructor.description or "",
            tagline=instructor.tagline or "",
            website_url=instructor.website_url or "",
            instagram_username=instructor.instagram_username or "",
            tiktok_username=instructor.tiktok_username or "",
            is_verified=bool(instructor.is_verified),
            instructor_since=instructor.instructor_since,
            location=instructor.location or "",
            last_spotify_playlist=instructor.last_spotify_playlist or "",
            last_apple_music_playlist=instructor.last_apple_music_playlist or "",
            last_youtube_music_playlist=instructor.last_youtube_music_playlist or "",
            profile_image=_profile_image_url(instructor.profile_image),
            is_active=bool(user.is_active),
            created=instructor.created,
            modified=instructor.modified,
        )


class AdminInstructorUpdateSchema(BaseModel):
    """Partial payload for staff instructor edits."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone_number: str | None = None
    description: str | None = None
    tagline: str | None = None
    website_url: str | None = None
    instagram_username: str | None = None
    tiktok_username: str | None = None
    is_verified: bool | None = None
    instructor_since: Optional[date] = None
    location: str | None = None
    last_spotify_playlist: str | None = None
    last_apple_music_playlist: str | None = None
    last_youtube_music_playlist: str | None = None
    is_active: bool | None = None


class AdminInstructorCreateSchema(BaseModel):
    """Payload to create an instructor from the staff admin."""

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    description: str | None = None
    tagline: str | None = None
    website_url: str | None = None
    instagram_username: str | None = None
    tiktok_username: str | None = None
    is_verified: bool = False
    instructor_since: Optional[date] = None
    location: str | None = None
    last_spotify_playlist: str | None = None
    last_apple_music_playlist: str | None = None
    last_youtube_music_playlist: str | None = None
    is_active: bool = True
