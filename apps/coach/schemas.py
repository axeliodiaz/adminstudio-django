from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CoachProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str | None = None
    last_name: str | None = None
    username: str | None = None
    email: str | None = None
    phone_number: str | None = None
    tagline: str = ""
    description: str = ""
    profile_image: str | None = None
    instagram_username: str = ""
    instructor_since: date | None = None
    total_classes_taught: int = 0
    specialties: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class CoachProfileUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tagline: str | None = None
    description: str | None = None
    instagram_username: str | None = None
    phone_number: str | None = None
    specialties: list[str] | None = None
    languages: list[str] | None = None
    certifications: list[str] | None = None
    first_name: str | None = None
    last_name: str | None = None


class CoachClassSchema(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    duration_minutes: int
    room_name: str | None = None
    booked: int = 0
    capacity: int | None = None
    status: str
    new_rider_count: int | None = None


class TodayTipSchema(BaseModel):
    title: str
    body: str | None = None


class TodaySchema(BaseModel):
    date: date
    tip: TodayTipSchema
    classes: list[CoachClassSchema]


class RosterClassSchema(BaseModel):
    id: UUID
    title: str
    start_time: datetime
    duration_minutes: int
    room_name: str | None = None
    booked: int = 0
    capacity: int | None = None


class RiderSchema(BaseModel):
    reservation_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    spot_number: int | None = None
    checked_in: bool = False
    is_first_class: bool = False


class RosterSchema(BaseModel):
    class_: RosterClassSchema = Field(alias="class")
    riders: list[RiderSchema]

    model_config = ConfigDict(populate_by_name=True)


class RiderNotesSchema(RiderSchema):
    seat_height: int | None = None
    seat_distance: int | None = None
    handlebar_distance: int | None = None
    shoe_size: float | None = None
    notes: str = ""
    alerts: list[str] = Field(default_factory=list)


class ClassNotesSchema(BaseModel):
    class_: RosterClassSchema = Field(alias="class")
    riders: list[RiderNotesSchema]

    model_config = ConfigDict(populate_by_name=True)


class CheckInSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    checked_in: bool


class ReservationNotesUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    notes: str = ""


class RiderSetupUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    seat_height: int | None = None
    seat_distance: int | None = None
    handlebar_distance: int | None = None
    cycling_shoe_size: float | None = None


class PlaylistTrackInSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str
    artist: str = ""
    bpm: int | None = None
    duration_seconds: int = 0


class PlaylistSegmentInSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    duration_minutes: int = 0
    bpm_range: str = ""
    tracks: list[PlaylistTrackInSchema] = Field(default_factory=list)


class PlaylistUpdateSchema(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str | None = None
    total_duration_minutes: int | None = None
    segments: list[PlaylistSegmentInSchema] = Field(default_factory=list)


class PlaylistTrackOutSchema(BaseModel):
    title: str
    artist: str = ""
    bpm: int | None = None
    duration_seconds: int = 0
    order: int = 0


class PlaylistSegmentOutSchema(BaseModel):
    name: str
    duration_minutes: int = 0
    bpm_range: str = ""
    order: int = 0
    tracks: list[PlaylistTrackOutSchema] = Field(default_factory=list)


class ClassPlaylistOutSchema(BaseModel):
    class_id: UUID
    class_title: str
    title: str = ""
    total_duration_minutes: int = 0
    segments: list[PlaylistSegmentOutSchema] = Field(default_factory=list)


class PlaylistTemplateSchema(BaseModel):
    id: UUID
    name: str


class RecentClassSchema(BaseModel):
    id: UUID
    title: str
    date: date
    riders: int
    capacity: int | None = None
    rating: float | None = None


class CoachStatsSchema(BaseModel):
    classes_this_month: int
    total_riders_month: int
    avg_occupancy_pct: int
    avg_rating: float | None = None
    rating_count: int = 0
    monthly_classes: list[int]
    monthly_occupancy: list[int]
    monthly_ratings: list[float]
    month_labels: list[str]
    recent_classes: list[RecentClassSchema]
