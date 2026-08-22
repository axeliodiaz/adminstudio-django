"""Member-facing activity stats for the authenticated rider dashboard."""

from collections import Counter
from datetime import date, timedelta

from django.utils import timezone

from apps.instructors.schemas import _profile_image_url
from apps.members.constants import (
    RESERVATION_STATUS_ATTENDED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_MISSED,
    RESERVATION_STATUS_RESERVED,
)
from apps.members.models import Member, Reservation
from apps.wallets.models import PlanPurchase, Wallet

STREAK_CHART_WEEKS = 4
HOUR_RANGE = range(6, 22)
TOP_COACHES = 5
TOP_CLASSES = 6
TOP_SPOTS = 5
CONSUMED_STATUSES = (
    RESERVATION_STATUS_RESERVED,
    RESERVATION_STATUS_ATTENDED,
    RESERVATION_STATUS_MISSED,
)


def get_member_stats(user, *, now=None) -> dict:
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    month_starts = _ytd_month_starts(today)
    week_starts = _last_n_week_starts(today, STREAK_CHART_WEEKS)

    member = Member.objects.filter(user=user, is_removed=False).first()
    plan = _active_plan(user, now)
    wallet = Wallet.objects.filter(user=user).first()
    is_unlimited = bool(plan and wallet and wallet.is_unlimited_membership_active) or (
        plan is not None and plan.classes_included is None
    )
    class_credits = int(wallet.class_credits) if wallet else 0
    guest_pass_credits = int(wallet.guest_pass_credits) if wallet else 0

    empty = _empty_payload(
        month_starts=month_starts,
        week_starts=week_starts,
        member_since=_member_since(member, user),
        plan_name=plan.name if plan else None,
        classes_included=None if is_unlimited or plan is None else plan.classes_included,
        is_unlimited=bool(is_unlimited and plan is not None),
        class_credits=class_credits,
        guest_pass_credits=guest_pass_credits,
    )
    if member is None:
        return empty

    reservations = list(
        Reservation.objects.filter(member=member, is_removed=False, schedule__is_removed=False)
        .exclude(status=RESERVATION_STATUS_CANCELLED)
        .select_related(
            "schedule__instructor__user",
            "schedule__room__studio",
        )
    )

    attended_local = []
    consumed_this_month = 0
    missed_count = 0
    upcoming_count = 0
    for reservation in reservations:
        schedule = reservation.schedule
        if schedule is None or schedule.start_time is None:
            continue
        local_dt = timezone.localtime(schedule.start_time)
        local_date = local_dt.date()
        if (
            reservation.status in CONSUMED_STATUSES
            and local_date.year == today.year
            and local_date.month == today.month
        ):
            consumed_this_month += 1
        if reservation.status == RESERVATION_STATUS_MISSED:
            missed_count += 1
        if reservation.status == RESERVATION_STATUS_RESERVED and schedule.start_time >= now:
            upcoming_count += 1
        if reservation.status == RESERVATION_STATUS_ATTENDED:
            attended_local.append((reservation, local_dt, schedule))

    monthly_classes = [0] * len(month_starts)
    monthly_ride_minutes = [0] * len(month_starts)
    month_index = {start: i for i, start in enumerate(month_starts)}
    instructor_counts = Counter()
    instructor_last = {}
    studio_counts = Counter()
    title_counts = Counter()
    spot_counts = Counter()
    hour_counts = [0] * 24
    weekday_counts = [0] * 7
    last_visit = None
    total_ride_minutes = 0
    attended_week_starts = set()
    classes_attended_total = 0

    for reservation, local_dt, schedule in attended_local:
        local_date = local_dt.date()
        duration = int(schedule.duration_minutes or 0)
        total_ride_minutes += duration
        classes_attended_total += 1
        if last_visit is None or local_date > last_visit:
            last_visit = local_date

        month_key = local_date.replace(day=1)
        idx = month_index.get(month_key)
        if idx is not None:
            monthly_classes[idx] += 1
            monthly_ride_minutes[idx] += duration

        attended_week_starts.add(_iso_week_start(local_date))
        hour_counts[local_dt.hour] += 1
        weekday_counts[local_date.weekday()] += 1

        title = (schedule.title or "").strip() or "Clase"
        title_counts[title] += 1

        if reservation.spot:
            spot_counts[int(reservation.spot)] += 1

        instructor = schedule.instructor
        if instructor is not None:
            instructor_counts[instructor.id] += 1
            previous = instructor_last.get(instructor.id)
            if previous is None or local_date > previous:
                instructor_last[instructor.id] = local_date

        studio = getattr(schedule.room, "studio", None) if schedule.room_id else None
        if studio is not None:
            studio_counts[studio.id] += 1

    weekly_streak = [start in attended_week_starts for start in week_starts]
    favorite = _favorite_instructor(instructor_counts, instructor_last, attended_local)
    preferred_studio = _preferred_studio_name(studio_counts, attended_local)
    completed_window = sum(monthly_classes)
    weeks_in_window = max(1, (today - month_starts[0]).days / 7)
    avg_per_week = round(completed_window / weeks_in_window, 1) if completed_window else 0
    attendance_rate = None
    settled = classes_attended_total + missed_count
    if settled:
        attendance_rate = round(100.0 * classes_attended_total / settled, 1)

    return {
        "plan_name": plan.name if plan else None,
        "member_since": _member_since(member, user),
        "preferred_studio": preferred_studio,
        "classes_completed": completed_window,
        "classes_attended_total": classes_attended_total,
        "classes_missed": missed_count,
        "classes_upcoming": upcoming_count,
        "classes_this_month": consumed_this_month,
        "classes_included": None if is_unlimited or plan is None else plan.classes_included,
        "is_unlimited": bool(is_unlimited and plan is not None),
        "class_credits": class_credits,
        "guest_pass_credits": guest_pass_credits,
        "avg_classes_per_week": avg_per_week,
        "attendance_rate": attendance_rate,
        "current_streak_weeks": _current_streak_weeks(today, attended_week_starts),
        "last_visit": last_visit.isoformat() if last_visit else None,
        "total_ride_minutes": total_ride_minutes,
        "monthly_labels": [start.isoformat()[:7] for start in month_starts],
        "monthly_classes": monthly_classes,
        "weekly_streak": weekly_streak,
        "monthly_ride_minutes": monthly_ride_minutes,
        "favorite_instructor": favorite,
        "top_instructors": _top_instructors(instructor_counts, attended_local),
        "favorite_classes": _top_named(title_counts, TOP_CLASSES),
        "preferred_hours": _preferred_hours(hour_counts),
        "weekday_classes": weekday_counts,
        "time_of_day": _time_of_day(hour_counts),
        "favorite_spots": _favorite_spots(spot_counts),
        "rider_persona": _rider_persona(weekday_counts, hour_counts),
    }


def _empty_payload(
    *,
    month_starts,
    week_starts,
    member_since,
    plan_name,
    classes_included,
    is_unlimited,
    class_credits,
    guest_pass_credits,
):
    return {
        "plan_name": plan_name,
        "member_since": member_since,
        "preferred_studio": None,
        "classes_completed": 0,
        "classes_attended_total": 0,
        "classes_missed": 0,
        "classes_upcoming": 0,
        "classes_this_month": 0,
        "classes_included": classes_included,
        "is_unlimited": is_unlimited,
        "class_credits": class_credits,
        "guest_pass_credits": guest_pass_credits,
        "avg_classes_per_week": 0,
        "attendance_rate": None,
        "current_streak_weeks": 0,
        "last_visit": None,
        "total_ride_minutes": 0,
        "monthly_labels": [start.isoformat()[:7] for start in month_starts],
        "monthly_classes": [0] * len(month_starts),
        "weekly_streak": [False] * len(week_starts),
        "monthly_ride_minutes": [0] * len(month_starts),
        "favorite_instructor": None,
        "top_instructors": [],
        "favorite_classes": [],
        "preferred_hours": _preferred_hours([0] * 24),
        "weekday_classes": [0] * 7,
        "time_of_day": _time_of_day([0] * 24),
        "favorite_spots": [],
        "rider_persona": None,
    }


def _member_since(member, user) -> str | None:
    if member is not None and member.created:
        return timezone.localtime(member.created).date().isoformat()
    if user.date_joined:
        joined = user.date_joined
        if timezone.is_aware(joined):
            joined = timezone.localtime(joined)
        return joined.date().isoformat()
    return None


def _active_plan(user, now):
    purchases = (
        PlanPurchase.objects.filter(user=user, activated_since__isnull=False)
        .select_related("plan")
        .order_by("-created")
    )
    for purchase in purchases:
        if purchase.end and purchase.end < now:
            continue
        return purchase.plan
    return None


def _ytd_month_starts(today: date) -> list[date]:
    return [date(today.year, month, 1) for month in range(1, today.month + 1)]


def _iso_week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def _last_n_week_starts(today: date, n: int) -> list[date]:
    current = _iso_week_start(today)
    return [current - timedelta(weeks=offset) for offset in range(n - 1, -1, -1)]


def _current_streak_weeks(today: date, attended_week_starts: set) -> int:
    week = _iso_week_start(today)
    if week not in attended_week_starts:
        week -= timedelta(weeks=1)
    streak = 0
    while week in attended_week_starts:
        streak += 1
        week -= timedelta(weeks=1)
    return streak


def _instructor_payload(instructor, classes_count: int) -> dict:
    user = instructor.user
    return {
        "id": str(instructor.id),
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "tagline": instructor.tagline or "",
        "instagram_username": instructor.instagram_username or "",
        "profile_image": _profile_image_url(instructor.profile_image),
        "classes": classes_count,
    }


def _favorite_instructor(counts: Counter, last_dates: dict, attended_local) -> dict | None:
    if not counts:
        return None
    max_count = max(counts.values())
    tied_ids = [instructor_id for instructor_id, count in counts.items() if count == max_count]
    favorite_id = max(tied_ids, key=lambda instructor_id: last_dates.get(instructor_id) or date.min)

    instructor = None
    for _reservation, _local_dt, schedule in attended_local:
        if schedule.instructor_id == favorite_id:
            instructor = schedule.instructor
            break
    if instructor is None:
        return None
    return _instructor_payload(instructor, counts[favorite_id])


def _top_instructors(counts: Counter, attended_local) -> list[dict]:
    by_id = {}
    for _reservation, _local_dt, schedule in attended_local:
        instructor = schedule.instructor
        if instructor is not None and instructor.id not in by_id:
            by_id[instructor.id] = instructor
    rows = []
    for instructor_id, count in counts.most_common(TOP_COACHES):
        instructor = by_id.get(instructor_id)
        if instructor is not None:
            rows.append(_instructor_payload(instructor, count))
    return rows


def _preferred_studio_name(counts: Counter, attended_local) -> str | None:
    if not counts:
        return None
    studio_id = counts.most_common(1)[0][0]
    for _reservation, _local_dt, schedule in attended_local:
        studio = getattr(schedule.room, "studio", None) if schedule.room_id else None
        if studio is not None and studio.id == studio_id:
            return studio.name
    return None


def _top_named(counts: Counter, limit: int) -> list[dict]:
    return [{"name": name, "count": count} for name, count in counts.most_common(limit)]


def _preferred_hours(hour_counts: list[int]) -> dict:
    hours = list(HOUR_RANGE)
    extra = [hour for hour, count in enumerate(hour_counts) if count and hour not in hours]
    hours = sorted(set(hours).union(extra))
    return {
        "labels": [f"{hour:02d}:00" for hour in hours],
        "values": [hour_counts[hour] for hour in hours],
    }


def _time_of_day(hour_counts: list[int]) -> dict:
    morning = sum(hour_counts[hour] for hour in range(5, 12))
    midday = sum(hour_counts[hour] for hour in range(12, 17))
    evening = sum(hour_counts[hour] for hour in range(17, 22))
    night = sum(hour_counts[hour] for hour in list(range(0, 5)) + list(range(22, 24)))
    return {
        "morning": morning,
        "midday": midday,
        "evening": evening,
        "night": night,
    }


def _favorite_spots(counts: Counter) -> list[dict]:
    return [{"spot": spot, "count": count} for spot, count in counts.most_common(TOP_SPOTS)]


def _rider_persona(weekday_counts: list[int], hour_counts: list[int]) -> dict | None:
    total = sum(hour_counts)
    if total == 0:
        return None
    weekend = weekday_counts[5] + weekday_counts[6]
    if weekend / total >= 0.5:
        return {"id": "weekend", "label": "Guerrero de fin de semana"}
    peak_hour = hour_counts.index(max(hour_counts))
    if peak_hour < 9:
        return {"id": "early", "label": "Madrugador"}
    if peak_hour < 12:
        return {"id": "morning", "label": "Ritmo matinal"}
    if peak_hour < 17:
        return {"id": "midday", "label": "Mediodía"}
    return {"id": "afterwork", "label": "After work"}
