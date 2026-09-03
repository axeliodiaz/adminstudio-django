"""Services for schedules app (renamed from schedules).

Provide schema-based service functions that delegate to domain logic in schedules/schedules.py.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List
from uuid import UUID

from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.members.models import Reservation, WaitlistEntry
from apps.members import constants as member_constants
from apps.schedules import constants
from apps.instructors.models import Instructor
from apps.schedules.models import Schedule, ScheduleInstructorSubstitution
from apps.schedules.schedules import (
    create_schedule as create_schedule_model,
    delete_schedule as delete_schedule_model,
    get_schedule_by_id as get_schedule_by_id_domain,
    get_schedules_list,
    update_schedule as update_schedule_model,
)
from apps.schedules.schemas import AdminScheduleSchema, ScheduleSchema


def create_schedule(
    *,
    instructor_id: UUID,
    start_time: datetime,
    duration_minutes: int,
    room_id: UUID,
    status: str,
    title: str = "",
    description: str | None = None,
) -> ScheduleSchema:
    """Create a schedule and return a ScheduleSchema.

    Delegates the creation logic to apps.schedules.schedules.create_schedule.
    """
    schedule = create_schedule_model(
        instructor_id=instructor_id,
        start_time=start_time,
        duration_minutes=duration_minutes,
        room_id=room_id,
        status=status,
        title=title,
        description=description,
    )
    return ScheduleSchema.model_validate(schedule)


def _annotate_occupancy(queryset):
    """Attach booked/waitlist counts in two aggregated queries instead of per row."""
    return queryset.annotate(
        booked_count=Count(
            "reservations",
            filter=Q(
                reservations__is_removed=False,
                reservations__status=member_constants.RESERVATION_STATUS_RESERVED,
            ),
            distinct=True,
        ),
        waitlist_count=Count(
            "waitlist_entries",
            filter=Q(
                waitlist_entries__is_removed=False,
                waitlist_entries__status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
            ),
            distinct=True,
        ),
    )


def _studio_address(schedule: Schedule) -> str | None:
    room = getattr(schedule, "room", None)
    studio = getattr(room, "studio", None) if room else None
    address = getattr(studio, "address", None) if studio else None
    value = getattr(address, "address", None) if address else None
    return value or None


def _schedule_display_fields(schedule: Schedule) -> dict:
    room = getattr(schedule, "room", None)
    studio = getattr(room, "studio", None) if room else None
    return {
        "instructor_name": _instructor_display_name(schedule),
        "room_name": room.name if room else "",
        "studio_id": studio.id if studio else None,
        "studio_name": studio.name if studio else None,
        "studio_address": _studio_address(schedule),
    }


def _schedule_occupancy(schedule: Schedule) -> dict:
    room = getattr(schedule, "room", None)
    capacity = room.capacity if room else None
    booked = getattr(schedule, "booked_count", None)
    if booked is None:
        booked = Reservation.objects.filter(
            schedule_id=schedule.id,
            status=member_constants.RESERVATION_STATUS_RESERVED,
            is_removed=False,
        ).count()
    waitlist_count = getattr(schedule, "waitlist_count", None)
    if waitlist_count is None:
        waitlist_count = WaitlistEntry.objects.filter(
            schedule_id=schedule.id,
            is_removed=False,
            status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
        ).count()
    return {
        "capacity": capacity,
        "booked_count": booked,
        "waitlist_count": waitlist_count,
        "is_full": bool(capacity is not None and booked >= capacity),
        **_schedule_display_fields(schedule),
    }


def to_schedule_schema_list(items: Iterable) -> List[ScheduleSchema]:
    """Convert iterable of Schedule model instances to a list of ScheduleSchema."""
    if hasattr(items, "annotate"):
        items = _annotate_occupancy(items)
    schemas = []
    for obj in items:
        schema = ScheduleSchema.model_validate(obj)
        schemas.append(schema.model_copy(update=_schedule_occupancy(obj)))
    return schemas


def get_schedule_schema_list(
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    instructor_id: UUID | str | None = None,
    instructor_ids: Iterable[UUID | str] | None = None,
    room_name: str | None = None,
    room_id: UUID | str | None = None,
    room_ids: Iterable[UUID | str] | None = None,
    title: str | None = None,
    titles: Iterable[str] | None = None,
    scheduled_only: bool = False,
) -> List[ScheduleSchema]:
    """Fetch schedules ordered by start_time and return as list of ScheduleSchema."""
    return to_schedule_schema_list(
        get_schedules_list(
            start_time=start_time,
            end_time=end_time,
            instructor_id=instructor_id,
            instructor_ids=instructor_ids,
            room_name=room_name,
            room_id=room_id,
            room_ids=room_ids,
            title=title,
            titles=titles,
            scheduled_only=scheduled_only,
        )
    )


def get_schedule_schema_by_id(schedule_id: UUID) -> ScheduleSchema:
    """Fetch schedule by id and return as ScheduleSchema.

    Delegates to apps.schedules.schedules.get_schedule_by_id.
    """
    schedule = get_schedule_by_id_domain(schedule_id)
    schema = ScheduleSchema.model_validate(schedule)
    return schema.model_copy(update=_schedule_occupancy(schedule))


def _user_display_name(user) -> str:
    if not user:
        return ""
    name = " ".join(part for part in [user.first_name, user.last_name] if part).strip()
    return name or user.username or user.email or ""


def _instructor_display_name(schedule: Schedule) -> str:
    return _user_display_name(getattr(schedule.instructor, "user", None))


def _instructor_name_from_instructor(instructor: Instructor | None) -> str:
    if not instructor:
        return ""
    return _user_display_name(getattr(instructor, "user", None))


def _serialize_substitution(row: ScheduleInstructorSubstitution) -> dict:
    return {
        "id": row.id,
        "old_instructor_id": row.old_instructor_id,
        "old_instructor_name": _instructor_name_from_instructor(row.old_instructor),
        "new_instructor_id": row.new_instructor_id,
        "new_instructor_name": _instructor_name_from_instructor(row.new_instructor),
        "changed_by_id": row.changed_by_id,
        "changed_by_name": _user_display_name(row.changed_by),
        "changed_at": row.created,
        "reason": row.reason or "",
        "notify": row.notify,
        "reserved_notified": row.reserved_notified,
        "waitlist_notified": row.waitlist_notified,
    }


def _serialize_admin_schedule(
    schedule: Schedule,
    *,
    copies_created: int | None = None,
    include_history: bool = False,
) -> dict:
    room = schedule.room
    studio = getattr(room, "studio", None)
    payload = {
        "id": schedule.id,
        "title": schedule.title or "",
        "description": schedule.description,
        "created": schedule.created,
        "modified": schedule.modified,
        "instructor_id": schedule.instructor_id,
        "instructor_name": _instructor_display_name(schedule),
        "start_time": schedule.start_time,
        "duration_minutes": schedule.duration_minutes,
        "room_id": schedule.room_id,
        "room_name": room.name if room else "",
        "studio_id": studio.id if studio else None,
        "studio_name": studio.name if studio else None,
        "room_capacity": room.capacity if room else None,
        "reservation_count": (
            getattr(schedule, "reservation_count", None)
            if getattr(schedule, "reservation_count", None) is not None
            else schedule.reservations.filter(
                is_removed=False,
                status=member_constants.RESERVATION_STATUS_RESERVED,
            ).count()
        ),
        "waitlist_count": (
            getattr(schedule, "waitlist_count", None)
            if getattr(schedule, "waitlist_count", None) is not None
            else WaitlistEntry.objects.filter(
                schedule_id=schedule.id,
                is_removed=False,
                status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
            ).count()
        ),
        "status": schedule.status,
        "cancellation_reason": schedule.cancellation_reason or "",
        "copies_created": copies_created,
        "substitutions": [],
    }
    if include_history:
        history = (
            ScheduleInstructorSubstitution.objects.filter(schedule_id=schedule.id)
            .select_related("old_instructor__user", "new_instructor__user", "changed_by")
            .order_by("-created")
        )
        payload["substitutions"] = [_serialize_substitution(row) for row in history]
    return AdminScheduleSchema.model_validate(payload).model_dump(mode="json")


def _admin_queryset():
    return (
        Schedule.objects.select_related("instructor__user", "room__studio")
        .annotate(
            reservation_count=Count(
                "reservations",
                filter=Q(
                    reservations__is_removed=False,
                    reservations__status=member_constants.RESERVATION_STATUS_RESERVED,
                ),
                distinct=True,
            ),
            waitlist_count=Count(
                "waitlist_entries",
                filter=Q(
                    waitlist_entries__is_removed=False,
                    waitlist_entries__status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
                ),
                distinct=True,
            ),
        )
        .order_by("start_time")
    )


def list_admin_schedules(
    *,
    search: str | None = None,
    status: str | None = None,
    instructor_id: str | UUID | None = None,
    room_id: str | UUID | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list[dict]:
    """Return non-deleted schedules for the staff admin calendar."""
    queryset = _admin_queryset()

    if status in constants.SCHEDULE_STATUSES:
        queryset = queryset.filter(status=status)
    if instructor_id:
        queryset = queryset.filter(instructor_id=instructor_id)
    if room_id:
        queryset = queryset.filter(room_id=room_id)
    if start_time is not None:
        queryset = queryset.filter(start_time__gte=start_time)
    if end_time is not None:
        queryset = queryset.filter(start_time__lte=end_time)

    term = (search or "").strip()
    if term:
        queryset = queryset.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(room__name__icontains=term)
            | Q(room__studio__name__icontains=term)
            | Q(instructor__user__first_name__icontains=term)
            | Q(instructor__user__last_name__icontains=term)
            | Q(instructor__user__username__icontains=term)
        ).distinct()

    return [_serialize_admin_schedule(schedule) for schedule in queryset]


def get_admin_schedule(*, schedule_id: str | UUID) -> dict:
    schedule = get_object_or_404(_admin_queryset(), id=schedule_id)
    return _serialize_admin_schedule(schedule, include_history=True)


def _validate_schedule_write(*, data: dict, require_required_fields: bool) -> None:
    if require_required_fields:
        if not data.get("instructor_id"):
            raise ValueError("El instructor es obligatorio.")
        if not data.get("room_id"):
            raise ValueError("La sala es obligatoria.")
        if data.get("start_time") is None:
            raise ValueError("La fecha y hora de inicio son obligatorias.")
        if data.get("duration_minutes") is None:
            raise ValueError("La duración es obligatoria.")

    if "title" in data and data["title"] is not None and not str(data["title"]).strip():
        raise ValueError("El título no puede estar vacío.")

    if "duration_minutes" in data and data["duration_minutes"] is not None:
        if int(data["duration_minutes"]) <= 0:
            raise ValueError("La duración debe ser un número positivo.")

    if (
        "status" in data
        and data["status"] is not None
        and data["status"] not in constants.SCHEDULE_STATUSES
    ):
        raise ValueError("El estado de la clase es inválido.")

    if "repeat_weeks" in data and data["repeat_weeks"] is not None:
        weeks = int(data["repeat_weeks"])
        if weeks < 1 or weeks > 16:
            raise ValueError("repeat_weeks debe estar entre 1 y 16.")


def create_admin_schedule(*, data: dict) -> dict:
    """Create one class, optionally repeating it weekly."""
    _validate_schedule_write(data=data, require_required_fields=True)

    title = str(data.get("title") or "").strip()
    weeks = int(data.get("repeat_weeks") or 1)
    created: list[Schedule] = []
    start_time = data["start_time"]

    for offset in range(weeks):
        schedule = create_schedule_model(
            instructor_id=data["instructor_id"],
            start_time=start_time + timedelta(weeks=offset),
            duration_minutes=int(data["duration_minutes"]),
            room_id=data["room_id"],
            status=data.get("status") or constants.SCHEDULE_STATUS_SCHEDULED,
            title=title,
            description=data.get("description"),
        )
        created.append(schedule)

    first = get_object_or_404(_admin_queryset(), id=created[0].id)
    return _serialize_admin_schedule(first, copies_created=len(created))


def update_admin_schedule(*, schedule_id: str | UUID, data: dict) -> dict:
    _validate_schedule_write(data=data, require_required_fields=False)
    if "repeat_weeks" in data:
        data = {key: value for key, value in data.items() if key != "repeat_weeks"}

    schedule = get_object_or_404(Schedule, id=schedule_id)
    if "title" in data and data["title"] is not None:
        data["title"] = str(data["title"]).strip()

    new_status = data.get("status")
    transitioning_to_canceled = (
        new_status == constants.SCHEDULE_STATUS_CANCELED
        and schedule.status != constants.SCHEDULE_STATUS_CANCELED
    )
    if transitioning_to_canceled:
        reason = data.get("cancellation_reason")
        if reason is None:
            reason = schedule.cancellation_reason or ""
        return cancel_admin_schedule(schedule_id=schedule.id, reason=str(reason or ""))

    update_schedule_model(schedule, data=data)
    return get_admin_schedule(schedule_id=schedule.id)


def cancel_admin_schedule(*, schedule_id: str | UUID, reason: str = "") -> dict:
    """Cancel a class: cascade to reservations (refund + email) and expire waitlist."""
    from apps.members.members import cancel_reservation
    from apps.members.waitlist import expire_waitlist_for_cancelled_schedule

    with transaction.atomic():
        schedule = get_object_or_404(
            Schedule.objects.select_for_update(), id=schedule_id, is_removed=False
        )
        if schedule.status != constants.SCHEDULE_STATUS_CANCELED:
            schedule.status = constants.SCHEDULE_STATUS_CANCELED
            schedule.cancellation_reason = (reason or "").strip()
            schedule.save(update_fields=["status", "cancellation_reason", "modified"])
        elif reason is not None and (reason or "").strip() != (schedule.cancellation_reason or ""):
            schedule.cancellation_reason = (reason or "").strip()
            schedule.save(update_fields=["cancellation_reason", "modified"])

        reserved_ids = list(
            Reservation.objects.filter(
                schedule_id=schedule.id,
                status=member_constants.RESERVATION_STATUS_RESERVED,
                is_removed=False,
            ).values_list("id", flat=True)
        )

    for reservation_id in reserved_ids:
        cancel_reservation(
            str(reservation_id),
            bypass_free_cancel_window=True,
            cancellation_source=member_constants.CANCELLATION_SOURCE_SCHEDULE,
            cancellation_reason=schedule.cancellation_reason,
            promote_waitlist=False,
        )

    expire_waitlist_for_cancelled_schedule(schedule.id)
    return get_admin_schedule(schedule_id=schedule.id)


def delete_admin_schedule(*, schedule_id: str | UUID) -> None:
    schedule = get_object_or_404(_admin_queryset(), id=schedule_id)
    reserved = int(getattr(schedule, "reservation_count", 0) or 0)
    if reserved > 0:
        raise ValueError(
            "No se puede eliminar una clase con reservas activas. "
            "Cáncela la clase o reubica a los socios primero."
        )
    delete_schedule_model(schedule)


def _schedule_end(start_time: datetime, duration_minutes: int) -> datetime:
    return start_time + timedelta(minutes=int(duration_minutes or 0))


def overlapping_schedules_for_instructor(
    *,
    instructor_id: str | UUID,
    start_time: datetime,
    duration_minutes: int,
    exclude_schedule_id: str | UUID | None = None,
) -> list[Schedule]:
    """Return non-canceled classes for this instructor that overlap the given window."""
    window_end = _schedule_end(start_time, duration_minutes)
    queryset = (
        Schedule.objects.filter(instructor_id=instructor_id, is_removed=False)
        .exclude(status=constants.SCHEDULE_STATUS_CANCELED)
        .filter(start_time__lt=window_end)
        .select_related("room__studio", "instructor__user")
        .order_by("start_time")
    )
    if exclude_schedule_id is not None:
        queryset = queryset.exclude(id=exclude_schedule_id)

    overlaps: list[Schedule] = []
    for other in queryset:
        if _schedule_end(other.start_time, other.duration_minutes) > start_time:
            overlaps.append(other)
    return overlaps


def _serialize_conflict(schedule: Schedule) -> dict:
    room = getattr(schedule, "room", None)
    studio = getattr(room, "studio", None) if room else None
    return {
        "id": str(schedule.id),
        "title": schedule.title or "",
        "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
        "duration_minutes": schedule.duration_minutes,
        "room_name": room.name if room else "",
        "studio_name": studio.name if studio else None,
        "status": schedule.status,
    }


def _load_substitute_instructor(instructor_id: str | UUID) -> Instructor:
    instructor = (
        Instructor.objects.select_related("user").filter(id=instructor_id, is_removed=False).first()
    )
    if instructor is None:
        raise ValueError("El instructor suplente no existe.")
    user = instructor.user
    if not user or not user.is_active:
        raise ValueError("El instructor suplente no está activo.")
    return instructor


def preview_substitute_coach(
    *,
    schedule_id: str | UUID,
    new_instructor_id: str | UUID | None = None,
) -> dict:
    schedule = get_object_or_404(
        Schedule.objects.select_related("instructor__user", "room__studio"),
        id=schedule_id,
        is_removed=False,
    )
    now = timezone.now()
    minutes_until_start = int((schedule.start_time - now).total_seconds() // 60)
    reservation_count = Reservation.objects.filter(
        schedule_id=schedule.id,
        status=member_constants.RESERVATION_STATUS_RESERVED,
        is_removed=False,
    ).count()
    waitlist_count = WaitlistEntry.objects.filter(
        schedule_id=schedule.id,
        is_removed=False,
        status__in=member_constants.WAITLIST_ACTIVE_STATUSES,
    ).count()

    payload = {
        "schedule_id": str(schedule.id),
        "status": schedule.status,
        "title": schedule.title or "",
        "start_time": schedule.start_time.isoformat() if schedule.start_time else None,
        "minutes_until_start": minutes_until_start,
        "starts_within_15_minutes": 0 <= minutes_until_start < 15,
        "old_instructor_id": str(schedule.instructor_id),
        "old_instructor_name": _instructor_display_name(schedule),
        "reservation_count": reservation_count,
        "waitlist_count": waitlist_count,
        "candidate": None,
    }

    if not new_instructor_id:
        return payload

    candidate: dict = {
        "instructor_id": str(new_instructor_id),
        "instructor_name": "",
        "eligible": False,
        "conflicts": [],
        "detail": None,
    }
    try:
        instructor = _load_substitute_instructor(new_instructor_id)
        candidate["instructor_name"] = _instructor_name_from_instructor(instructor)
        if str(instructor.id) == str(schedule.instructor_id):
            raise ValueError("El suplente debe ser distinto al instructor actual.")
        if schedule.status == constants.SCHEDULE_STATUS_CANCELED:
            raise ValueError("No se puede asignar un suplente a una clase cancelada.")
        conflicts = overlapping_schedules_for_instructor(
            instructor_id=instructor.id,
            start_time=schedule.start_time,
            duration_minutes=schedule.duration_minutes,
            exclude_schedule_id=schedule.id,
        )
        candidate["conflicts"] = [_serialize_conflict(item) for item in conflicts]
        if conflicts:
            raise ValueError("El instructor tiene otra clase en el mismo horario.")
        candidate["eligible"] = True
    except ValueError as exc:
        candidate["detail"] = str(exc)
    payload["candidate"] = candidate
    return payload


def substitute_coach(
    *,
    schedule_id: str | UUID,
    new_instructor_id: str | UUID,
    reason: str = "",
    notify: bool = True,
    changed_by=None,
) -> dict:
    """Replace the class instructor, persist history, and optionally email riders."""
    from apps.members.notifications import send_coach_substituted_email
    from apps.members.waitlist import active_waitlist_queryset

    notify = bool(notify)
    reason_text = (reason or "").strip()

    with transaction.atomic():
        schedule = get_object_or_404(
            Schedule.objects.select_for_update().select_related("instructor__user", "room__studio"),
            id=schedule_id,
            is_removed=False,
        )
        if schedule.status == constants.SCHEDULE_STATUS_CANCELED:
            raise ValueError("No se puede asignar un suplente a una clase cancelada.")

        new_instructor = _load_substitute_instructor(new_instructor_id)
        if new_instructor.id == schedule.instructor_id:
            raise ValueError("El suplente debe ser distinto al instructor actual.")

        conflicts = overlapping_schedules_for_instructor(
            instructor_id=new_instructor.id,
            start_time=schedule.start_time,
            duration_minutes=schedule.duration_minutes,
            exclude_schedule_id=schedule.id,
        )
        if conflicts:
            raise ValueError("El instructor tiene otra clase en el mismo horario.")

        old_instructor = schedule.instructor
        old_name = _instructor_name_from_instructor(old_instructor) or "Coach"
        new_name = _instructor_name_from_instructor(new_instructor) or "Coach"

        schedule.instructor = new_instructor
        schedule.save(update_fields=["instructor", "modified"])

        from apps.coach.models import ClassPlaylist

        ClassPlaylist.objects.filter(schedule_id=schedule.id).update(instructor=new_instructor)

        reserved = list(
            Reservation.objects.filter(
                schedule_id=schedule.id,
                status=member_constants.RESERVATION_STATUS_RESERVED,
                is_removed=False,
            ).select_related("member__user")
        )
        waitlisted = list(active_waitlist_queryset(schedule.id).select_related("member__user"))

        reserved_notified = len(reserved) if notify else 0
        waitlist_notified = len(waitlisted) if notify else 0

        substitution = ScheduleInstructorSubstitution.objects.create(
            schedule=schedule,
            old_instructor=old_instructor,
            new_instructor=new_instructor,
            changed_by=changed_by if getattr(changed_by, "is_authenticated", False) else None,
            reason=reason_text,
            notify=notify,
            reserved_notified=reserved_notified,
            waitlist_notified=waitlist_notified,
        )

    if notify:
        for reservation in reserved:
            send_coach_substituted_email(
                user=reservation.member.user,
                schedule=schedule,
                old_coach_name=old_name,
                new_coach_name=new_name,
                reason=reason_text,
                audience="reservation",
            )
        for entry in waitlisted:
            send_coach_substituted_email(
                user=entry.member.user,
                schedule=schedule,
                old_coach_name=old_name,
                new_coach_name=new_name,
                reason=reason_text,
                audience="waitlist",
            )

    result = get_admin_schedule(schedule_id=schedule.id)
    result["substitution"] = _serialize_substitution(substitution)
    return result
