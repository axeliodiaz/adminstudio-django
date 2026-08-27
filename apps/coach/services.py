from __future__ import annotations

from datetime import date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from apps.coach import constants
from apps.coach.exceptions import CoachClassNotFound, CoachReservationNotFound
from apps.coach.models import ClassPlaylist, PlaylistSegment, PlaylistTemplate, PlaylistTrack
from apps.instructors.models import Instructor
from apps.members import constants as member_constants
from apps.members.models import Reservation
from apps.schedules import constants as schedule_constants
from apps.schedules.models import Schedule
from apps.users.models import User

TZ = constants.COACH_TIMEZONE


def get_instructor_for_user(user: User) -> Instructor:
    return Instructor.objects.select_related("user").get(user_id=user.pk, is_removed=False)


def _profile_image_url(value) -> str | None:
    """Return a usable image URL. Absolute http(s) names are returned as-is."""
    try:
        name = getattr(value, "name", None) or ""
        if not name:
            return None
        name_str = str(name)
        if name_str.startswith(("http://", "https://")):
            return name_str
        return value.url
    except Exception:
        return None


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _local_now() -> datetime:
    return timezone.now().astimezone(TZ)


def _local_today() -> date:
    return _local_now().date()


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=TZ)
    end = datetime.combine(day, time.max, tzinfo=TZ)
    return start, end


def _parse_date(raw: str | None, default: date) -> date:
    if not raw:
        return default
    return date.fromisoformat(raw)


def _parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if timezone.is_naive(value):
        value = value.replace(tzinfo=TZ)
    return value


def _week_bounds(day: date) -> tuple[datetime, datetime]:
    monday = day - timedelta(days=day.weekday())
    sunday = monday + timedelta(days=6)
    start, _ = _day_bounds(monday)
    _, end = _day_bounds(sunday)
    return start, end


def _class_end(schedule: Schedule) -> datetime:
    start = schedule.start_time
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    return start + timedelta(minutes=schedule.duration_minutes or 0)


def _booked_count(schedule: Schedule) -> int:
    occupied = getattr(schedule, "occupied", None)
    if occupied is not None:
        return occupied
    return Reservation.objects.filter(
        schedule_id=schedule.id,
        is_removed=False,
        status__in=constants.OCCUPIED_STATUSES,
    ).count()


def _capacity(schedule: Schedule) -> int | None:
    room = getattr(schedule, "room", None)
    return room.capacity if room else None


def _room_name(schedule: Schedule) -> str | None:
    room = getattr(schedule, "room", None)
    return room.name if room else None


def _display_status(schedule: Schedule, now: datetime | None = None) -> str:
    now = now or timezone.now()
    if _class_end(schedule) < now:
        return constants.CLASS_STATUS_COMPLETED
    capacity = _capacity(schedule)
    booked = _booked_count(schedule)
    if capacity is not None and booked >= capacity:
        return constants.CLASS_STATUS_FULL
    return constants.CLASS_STATUS_UPCOMING


def _coach_schedules(instructor: Instructor):
    return (
        Schedule.objects.filter(instructor=instructor, is_removed=False)
        .select_related("room")
        .annotate(
            occupied=Count(
                "reservations",
                filter=Q(
                    reservations__is_removed=False,
                    reservations__status__in=constants.OCCUPIED_STATUSES,
                ),
            )
        )
        .exclude(status=schedule_constants.SCHEDULE_STATUS_CANCELED)
    )


def get_coach_schedule(instructor: Instructor, schedule_id: UUID) -> Schedule:
    try:
        return _coach_schedules(instructor).get(pk=schedule_id)
    except Schedule.DoesNotExist as exc:
        raise CoachClassNotFound(constants.CLASS_NOT_FOUND_DETAIL) from exc


def _total_classes_taught(instructor: Instructor) -> int:
    now = timezone.now()
    return (
        Schedule.objects.filter(
            instructor=instructor,
            is_removed=False,
        )
        .exclude(status=schedule_constants.SCHEDULE_STATUS_CANCELED)
        .filter(Q(status=schedule_constants.SCHEDULE_STATUS_COMPLETED) | Q(start_time__lt=now))
        .count()
    )


def get_coach_profile(instructor: Instructor) -> dict:
    user = instructor.user
    return {
        "id": instructor.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "username": user.username,
        "email": user.email,
        "phone_number": user.phone_number,
        "tagline": instructor.tagline or "",
        "description": instructor.description or "",
        "profile_image": _profile_image_url(instructor.profile_image),
        "instagram_username": instructor.instagram_username or "",
        "instructor_since": instructor.instructor_since,
        "total_classes_taught": _total_classes_taught(instructor),
        "specialties": _as_list(instructor.specialties),
        "languages": _as_list(instructor.languages),
        "certifications": _as_list(instructor.certifications),
    }


def update_coach_profile(instructor: Instructor, data: dict) -> dict:
    user = instructor.user
    user_fields = []
    for field in ("first_name", "last_name", "phone_number"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
            user_fields.append(field)
    if user_fields:
        user.save(update_fields=user_fields)

    instructor_fields = []
    for field in (
        "tagline",
        "description",
        "instagram_username",
        "specialties",
        "languages",
        "certifications",
    ):
        if field in data and data[field] is not None:
            setattr(instructor, field, data[field])
            instructor_fields.append(field)
    if instructor_fields:
        instructor.save(update_fields=instructor_fields)
    instructor.refresh_from_db()
    instructor.user.refresh_from_db()
    return get_coach_profile(instructor)


def _class_payload(schedule: Schedule, *, include_new_riders: bool = False) -> dict:
    payload = {
        "id": schedule.id,
        "title": schedule.title,
        "start_time": schedule.start_time,
        "duration_minutes": schedule.duration_minutes,
        "room_name": _room_name(schedule),
        "booked": _booked_count(schedule),
        "capacity": _capacity(schedule),
        "status": _display_status(schedule),
    }
    if include_new_riders:
        payload["new_rider_count"] = _new_rider_count(schedule)
    return payload


def _first_reservation_ids(member_ids: list) -> dict:
    if not member_ids:
        return {}
    rows = (
        Reservation.objects.filter(member_id__in=member_ids, is_removed=False)
        .exclude(status=member_constants.RESERVATION_STATUS_CANCELLED)
        .select_related("schedule")
        .order_by("member_id", "schedule__start_time", "created")
    )
    first_ids = {}
    for reservation in rows:
        first_ids.setdefault(reservation.member_id, reservation.id)
    return first_ids


def _new_rider_count(schedule: Schedule) -> int:
    reservations = list(
        Reservation.objects.filter(
            schedule_id=schedule.id,
            is_removed=False,
            status__in=constants.ROSTER_STATUSES,
        )
    )
    member_ids = [item.member_id for item in reservations]
    first_ids = _first_reservation_ids(member_ids)
    return sum(1 for item in reservations if first_ids.get(item.member_id) == item.id)


def _format_local_time(schedule: Schedule) -> str:
    local = schedule.start_time.astimezone(TZ)
    return local.strftime("%H:%M")


def _today_tip(day: date, classes: list[Schedule]) -> dict:
    new_bits = []
    total_new = 0
    for schedule in classes:
        count = _new_rider_count(schedule)
        if count:
            total_new += count
            noun = "rider nuevo" if count == 1 else "riders nuevos"
            new_bits.append(f"{count} {noun} en la clase de las {_format_local_time(schedule)}")
    if new_bits:
        body = " — ".join(new_bits) + " — recuerda explicar ajuste de bike."
    else:
        body = constants.GENERIC_TIPS[day.toordinal() % len(constants.GENERIC_TIPS)]
    return {"title": constants.TIP_TITLE, "body": body}


def get_today(instructor: Instructor, raw_date: str | None = None) -> dict:
    day = _parse_date(raw_date, _local_today())
    start, end = _day_bounds(day)
    classes = list(
        _coach_schedules(instructor)
        .filter(start_time__gte=start, start_time__lte=end)
        .order_by("start_time")
    )
    return {
        "date": day,
        "tip": _today_tip(day, classes),
        "classes": [_class_payload(item, include_new_riders=True) for item in classes],
    }


def list_schedules(instructor: Instructor, raw_from: str | None, raw_to: str | None) -> list[dict]:
    start = _parse_datetime(raw_from)
    end = _parse_datetime(raw_to)
    if start is None or end is None:
        start, end = _week_bounds(_local_today())
    qs = (
        _coach_schedules(instructor)
        .filter(start_time__gte=start, start_time__lte=end)
        .order_by("start_time")
    )
    return [_class_payload(item) for item in qs]


def get_class(instructor: Instructor, schedule_id: UUID) -> dict:
    return _class_payload(get_coach_schedule(instructor, schedule_id), include_new_riders=True)


def _roster_reservations(schedule: Schedule):
    return (
        Reservation.objects.filter(
            schedule=schedule,
            is_removed=False,
            status__in=constants.ROSTER_STATUSES,
        )
        .select_related("member__user")
        .order_by("spot", "member__user__first_name", "member__user__last_name")
    )


def _rider_payload(reservation: Reservation, first_ids: dict) -> dict:
    user = reservation.member.user
    return {
        "reservation_id": reservation.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "spot_number": reservation.spot,
        "checked_in": reservation.status == member_constants.RESERVATION_STATUS_ATTENDED,
        "is_first_class": first_ids.get(reservation.member_id) == reservation.id,
    }


def get_roster(instructor: Instructor, schedule_id: UUID) -> dict:
    schedule = get_coach_schedule(instructor, schedule_id)
    reservations = list(_roster_reservations(schedule))
    first_ids = _first_reservation_ids([item.member_id for item in reservations])
    return {
        "class": {
            "id": schedule.id,
            "title": schedule.title,
            "start_time": schedule.start_time,
            "duration_minutes": schedule.duration_minutes,
            "room_name": _room_name(schedule),
            "booked": _booked_count(schedule),
            "capacity": _capacity(schedule),
        },
        "riders": [_rider_payload(item, first_ids) for item in reservations],
    }


def _get_coach_reservation(instructor: Instructor, reservation_id: UUID) -> Reservation:
    try:
        return Reservation.objects.select_related("member__user", "schedule__room").get(
            pk=reservation_id,
            is_removed=False,
            schedule__instructor=instructor,
            schedule__is_removed=False,
        )
    except Reservation.DoesNotExist as exc:
        raise CoachReservationNotFound(constants.RESERVATION_NOT_FOUND_DETAIL) from exc


def check_in_reservation(instructor: Instructor, reservation_id: UUID, checked_in: bool) -> dict:
    reservation = _get_coach_reservation(instructor, reservation_id)
    reservation.status = (
        member_constants.RESERVATION_STATUS_ATTENDED
        if checked_in
        else member_constants.RESERVATION_STATUS_RESERVED
    )
    reservation.save(update_fields=["status"])
    first_ids = _first_reservation_ids([reservation.member_id])
    return _rider_payload(reservation, first_ids)


def start_class(instructor: Instructor, schedule_id: UUID) -> dict:
    schedule = get_coach_schedule(instructor, schedule_id)
    if schedule.status in (
        schedule_constants.SCHEDULE_STATUS_DRAFT,
        schedule_constants.SCHEDULE_STATUS_SCHEDULED,
    ):
        schedule.status = schedule_constants.SCHEDULE_STATUS_SCHEDULED
        schedule.save(update_fields=["status"])
    return {"ok": True, "status": schedule.status}


def _shoe_size(user) -> float | None:
    value = user.cycling_shoe_size if user.cycling_shoe_size is not None else user.shoe_size
    return float(value) if value is not None else None


def _alerts(reservation: Reservation, is_first_class: bool, user) -> list[str]:
    alerts = []
    if is_first_class:
        alerts.append("Primera clase")
        if user.seat_height is None:
            alerts.append("Setup pendiente")
    notes = (reservation.notes or "").lower()
    if any(keyword in notes for keyword in constants.INJURY_KEYWORDS):
        alerts.append("Lesión activa")
    return alerts


def get_class_notes(instructor: Instructor, schedule_id: UUID) -> dict:
    roster = get_roster(instructor, schedule_id)
    schedule = get_coach_schedule(instructor, schedule_id)
    reservations = {item.id: item for item in _roster_reservations(schedule)}
    riders = []
    for rider in roster["riders"]:
        reservation = reservations[rider["reservation_id"]]
        user = reservation.member.user
        riders.append(
            {
                **rider,
                "seat_height": user.seat_height,
                "seat_distance": user.seat_distance,
                "handlebar_distance": user.handlebar_distance,
                "shoe_size": _shoe_size(user),
                "notes": reservation.notes or "",
                "alerts": _alerts(reservation, rider["is_first_class"], user),
            }
        )
    return {"class": roster["class"], "riders": riders}


def update_reservation_notes(instructor: Instructor, reservation_id: UUID, notes: str) -> dict:
    reservation = _get_coach_reservation(instructor, reservation_id)
    reservation.notes = notes
    reservation.save(update_fields=["notes"])
    first_ids = _first_reservation_ids([reservation.member_id])
    user = reservation.member.user
    rider = _rider_payload(reservation, first_ids)
    return {
        **rider,
        "seat_height": user.seat_height,
        "seat_distance": user.seat_distance,
        "handlebar_distance": user.handlebar_distance,
        "shoe_size": _shoe_size(user),
        "notes": reservation.notes or "",
        "alerts": _alerts(reservation, rider["is_first_class"], user),
    }


def update_rider_setup(instructor: Instructor, reservation_id: UUID, data: dict) -> dict:
    reservation = _get_coach_reservation(instructor, reservation_id)
    user = reservation.member.user
    fields = []
    for field in ("seat_height", "seat_distance", "handlebar_distance", "cycling_shoe_size"):
        if field in data and data[field] is not None:
            setattr(user, field, data[field])
            fields.append(field)
    if fields:
        user.save(update_fields=fields)
        user.refresh_from_db()
    first_ids = _first_reservation_ids([reservation.member_id])
    rider = _rider_payload(reservation, first_ids)
    return {
        **rider,
        "seat_height": user.seat_height,
        "seat_distance": user.seat_distance,
        "handlebar_distance": user.handlebar_distance,
        "shoe_size": _shoe_size(user),
        "notes": reservation.notes or "",
        "alerts": _alerts(reservation, rider["is_first_class"], user),
    }


def _empty_playlist(schedule: Schedule) -> dict:
    return {
        "class_id": schedule.id,
        "class_title": schedule.title,
        "title": "",
        "total_duration_minutes": 0,
        "segments": [],
    }


def get_playlist(instructor: Instructor, schedule_id: UUID) -> dict:
    schedule = get_coach_schedule(instructor, schedule_id)
    try:
        playlist = ClassPlaylist.objects.prefetch_related(
            Prefetch(
                "segments",
                queryset=PlaylistSegment.objects.filter(is_removed=False).prefetch_related(
                    Prefetch("tracks", queryset=PlaylistTrack.objects.filter(is_removed=False))
                ),
            )
        ).get(schedule=schedule, instructor=instructor, is_removed=False)
    except ClassPlaylist.DoesNotExist:
        return _empty_playlist(schedule)
    return {
        "class_id": schedule.id,
        "class_title": schedule.title,
        "title": playlist.title,
        "total_duration_minutes": playlist.total_duration_minutes,
        "segments": [
            {
                "name": segment.name,
                "duration_minutes": segment.duration_minutes,
                "bpm_range": segment.bpm_range,
                "order": segment.order,
                "tracks": [
                    {
                        "title": track.title,
                        "artist": track.artist,
                        "bpm": track.bpm,
                        "duration_seconds": track.duration_seconds,
                        "order": track.order,
                    }
                    for track in segment.tracks.all()
                ],
            }
            for segment in playlist.segments.all()
        ],
    }


def upsert_playlist(instructor: Instructor, schedule_id: UUID, data: dict) -> dict:
    schedule = get_coach_schedule(instructor, schedule_id)
    segments_data = data.get("segments") or []
    total = data.get("total_duration_minutes")
    if total is None:
        total = sum(item.get("duration_minutes") or 0 for item in segments_data)
    playlist, _ = ClassPlaylist.objects.update_or_create(
        schedule=schedule,
        defaults={
            "instructor": instructor,
            "title": data.get("title") or schedule.title,
            "total_duration_minutes": total,
            "is_removed": False,
        },
    )
    PlaylistSegment.objects.filter(playlist=playlist).delete()
    for index, segment_data in enumerate(segments_data):
        segment = PlaylistSegment.objects.create(
            playlist=playlist,
            name=segment_data["name"],
            order=index,
            duration_minutes=segment_data.get("duration_minutes") or 0,
            bpm_range=segment_data.get("bpm_range") or "",
        )
        for track_index, track_data in enumerate(segment_data.get("tracks") or []):
            PlaylistTrack.objects.create(
                segment=segment,
                title=track_data["title"],
                artist=track_data.get("artist") or "",
                bpm=track_data.get("bpm"),
                duration_seconds=track_data.get("duration_seconds") or 0,
                order=track_index,
            )
    return get_playlist(instructor, schedule_id)


def list_playlist_templates(instructor: Instructor) -> list[dict]:
    return list(
        PlaylistTemplate.objects.filter(instructor=instructor, is_removed=False)
        .order_by("name")
        .values("id", "name")
    )


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _shift_month(day: date, delta: int) -> date:
    month = day.month + delta
    year = day.year
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return date(year, month, 1)


def _occupancy_pct(booked: int, capacity: int | None) -> int | None:
    if not capacity:
        return None
    return int(round(100 * booked / capacity))


def get_stats(instructor: Instructor, months: int = 6) -> dict:
    months = max(1, min(months, 24))
    today = _local_today()
    current_month = _month_start(today)
    range_start = _shift_month(current_month, -(months - 1))
    start_dt, _ = _day_bounds(range_start)
    _, end_dt = _day_bounds(_shift_month(current_month, 1) - timedelta(days=1))

    schedules = list(
        _coach_schedules(instructor)
        .filter(start_time__gte=start_dt, start_time__lte=end_dt)
        .select_related("room", "class_rating")
        .order_by("start_time")
    )
    month_keys = [_shift_month(range_start, index) for index in range(months)]
    buckets = {
        key: {"classes": 0, "booked": 0, "capacity": 0, "ratings": [], "rating_count": 0}
        for key in month_keys
    }
    this_month_classes = 0
    this_month_riders = 0
    this_month_capacity = 0
    ratings = []
    rating_count_total = 0

    for schedule in schedules:
        local_day = schedule.start_time.astimezone(TZ).date()
        key = _month_start(local_day)
        if key not in buckets:
            continue
        booked = _booked_count(schedule)
        capacity = _capacity(schedule) or 0
        buckets[key]["classes"] += 1
        buckets[key]["booked"] += booked
        buckets[key]["capacity"] += capacity
        rating = getattr(schedule, "class_rating", None)
        if rating and not rating.is_removed:
            buckets[key]["ratings"].append(float(rating.rating))
            buckets[key]["rating_count"] += rating.rating_count or 0
            ratings.append(float(rating.rating))
            rating_count_total += rating.rating_count or 0
        if key == current_month:
            this_month_classes += 1
            this_month_riders += booked
            this_month_capacity += capacity

    monthly_classes = [buckets[key]["classes"] for key in month_keys]
    monthly_occupancy = []
    monthly_ratings = []
    for key in month_keys:
        bucket = buckets[key]
        pct = _occupancy_pct(bucket["booked"], bucket["capacity"] or None)
        monthly_occupancy.append(pct if pct is not None else 0)
        monthly_ratings.append(
            round(sum(bucket["ratings"]) / len(bucket["ratings"]), 1) if bucket["ratings"] else 0.0
        )

    avg_occupancy = _occupancy_pct(this_month_riders, this_month_capacity or None) or 0
    past = list(
        _coach_schedules(instructor)
        .filter(start_time__lt=timezone.now())
        .select_related("room", "class_rating")
        .order_by("-start_time")[:8]
    )
    recent = []
    for schedule in past:
        rating_obj = getattr(schedule, "class_rating", None)
        recent.append(
            {
                "id": schedule.id,
                "title": schedule.title,
                "date": schedule.start_time.astimezone(TZ).date(),
                "riders": _booked_count(schedule),
                "capacity": _capacity(schedule),
                "rating": (
                    float(rating_obj.rating) if rating_obj and not rating_obj.is_removed else None
                ),
            }
        )

    return {
        "classes_this_month": this_month_classes,
        "total_riders_month": this_month_riders,
        "avg_occupancy_pct": avg_occupancy,
        "avg_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "rating_count": rating_count_total,
        "monthly_classes": monthly_classes,
        "monthly_occupancy": monthly_occupancy,
        "monthly_ratings": monthly_ratings,
        "month_labels": [constants.MONTH_LABELS_ES[key.month - 1] for key in month_keys],
        "recent_classes": recent,
    }


def build_ics(instructor: Instructor, raw_from: str | None, raw_to: str | None) -> str:
    events = list_schedules(instructor, raw_from, raw_to)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//PulseFit//Coach//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    stamp = timezone.now().strftime("%Y%m%dT%H%M%SZ")
    for item in events:
        start = item["start_time"]
        if timezone.is_naive(start):
            start = timezone.make_aware(start)
        start_utc = start.astimezone(ZoneInfo("UTC"))
        end_utc = (start + timedelta(minutes=item["duration_minutes"] or 0)).astimezone(
            ZoneInfo("UTC")
        )
        uid = f"{item['id']}@{settings.EMAIL_DOMAIN}"
        summary = item["title"].replace(",", r"\,")
        location = (item.get("room_name") or "").replace(",", r"\,")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTAMP:{stamp}",
                f"DTSTART:{start_utc.strftime('%Y%m%dT%H%M%SZ')}",
                f"DTEND:{end_utc.strftime('%Y%m%dT%H%M%SZ')}",
                f"SUMMARY:{summary}",
                f"LOCATION:{location}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"
