"""Build the PulseFit admin operational dashboard payload from live data."""

from collections import defaultdict
from datetime import datetime, time, timedelta

from django.db.models import Count, Prefetch, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.analytics.constants import (
    CLASS_FORMATS,
    CLP_PER_MXN,
    CLP_PER_USD,
    DEMO_PLAN_PREFIX,
    EXCLUDED_SCHEDULE_STATUSES,
    OCCUPIED_RESERVATION_STATUSES,
)
from apps.members.constants import RESERVATION_STATUS_CANCELLED, RESERVATION_STATUS_MISSED
from apps.members.models import Member, Reservation
from apps.schedules.models import Schedule
from apps.wallets.models import PlanPurchase, Wallet


def get_admin_dashboard(*, now=None) -> dict:
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    week_start = today - timedelta(days=6)
    prev_week_start = today - timedelta(days=13)
    prev_week_end = today - timedelta(days=7)
    last_30 = today - timedelta(days=29)
    revenue_start = today - timedelta(days=6)
    prev_revenue_start = today - timedelta(days=13)
    prev_revenue_end = today - timedelta(days=7)

    occupied_filter = Q(
        reservations__is_removed=False,
        reservations__status__in=OCCUPIED_RESERVATION_STATUSES,
    )

    schedules = (
        Schedule.objects.filter(is_removed=False)
        .exclude(status__in=EXCLUDED_SCHEDULE_STATUSES)
        .select_related("instructor__user", "room")
        .annotate(occupied=Count("reservations", filter=occupied_filter))
    )

    week_schedules = _in_local_date_range(schedules, week_start, today)
    prev_week_schedules = _in_local_date_range(schedules, prev_week_start, prev_week_end)
    month_schedules = list(_in_local_date_range(schedules, last_30, today))

    week_occ = _mean_occupancy(week_schedules)
    prev_week_occ = _mean_occupancy(prev_week_schedules)

    reservations_by_day = _reservation_counts_by_day(last_30, today)
    reservations_today = reservations_by_day.get(today, 0)
    reservations_yesterday = reservations_by_day.get(today - timedelta(days=1), 0)

    active_qs = _active_members_qs(today)
    active_members = active_qs.count()
    members_week_ago = _active_members_qs(today, created_on_or_before=prev_week_end).count()
    members_delta_pct = _pct_change(active_members, members_week_ago)

    revenue_7d = _revenue_between(revenue_start, today)
    revenue_prev = _revenue_between(prev_revenue_start, prev_revenue_end)
    wallet_stats = _wallet_commerce(today, revenue_start, last_30)

    return {
        "kpis": {
            "weekly_occupancy": {
                "value": week_occ,
                "delta_pp": (
                    round(week_occ - prev_week_occ, 1) if prev_week_occ is not None else None
                ),
            },
            "reservations_today": {
                "value": reservations_today,
                "previous": reservations_yesterday,
            },
            "active_members": {
                "value": active_members,
                "delta_pct": members_delta_pct,
            },
            "revenue_7d": {
                "amount_clp": revenue_7d,
                "amount_usd": _convert_clp(revenue_7d, CLP_PER_USD),
                "amount_mxn": _convert_clp(revenue_7d, CLP_PER_MXN),
                "delta_pct": _pct_change(revenue_7d, revenue_prev),
                "fx": {
                    "base": "CLP",
                    "clp_per_usd": CLP_PER_USD,
                    "clp_per_mxn": CLP_PER_MXN,
                },
            },
            "purchases_7d": wallet_stats["purchases_7d"],
            "unlimited_wallets": wallet_stats["unlimited_wallets"],
            "class_credits_outstanding": wallet_stats["class_credits_outstanding"],
            "guest_passes_outstanding": wallet_stats["guest_passes_outstanding"],
        },
        "reservations_30d": _reservations_30d_series(reservations_by_day, last_30, today),
        "occupancy_by_instructor": _occupancy_by_instructor(month_schedules),
        "plan_mix": _plan_mix(today, active_qs),
        "demand_by_format": _demand_by_format(month_schedules),
        "classes_vs_noshows": _classes_vs_noshows(week_start, today),
        "schedule_vs_occupancy": _schedule_vs_occupancy(month_schedules),
        "revenue_by_plan": wallet_stats["revenue_by_plan"],
        "purchases_30d": wallet_stats["purchases_30d"],
        "recent_purchases": wallet_stats["recent_purchases"],
    }


def _in_local_date_range(qs, start, end):
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))
    return qs.filter(start_time__gte=start_dt, start_time__lte=end_dt)


def _occupancy_pct(occupied: int, capacity: int) -> float | None:
    if not capacity:
        return None
    return round(100.0 * occupied / capacity, 1)


def _mean_occupancy(schedule_qs) -> float | None:
    rows = list(schedule_qs.values_list("occupied", "room__capacity"))
    if not rows:
        return None
    ratios = []
    for occupied, capacity in rows:
        pct = _occupancy_pct(occupied or 0, capacity or 0)
        if pct is not None:
            ratios.append(pct)
    if not ratios:
        return None
    return round(sum(ratios) / len(ratios), 1)


def _reservation_counts_by_day(start, end) -> dict:
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))
    rows = (
        Reservation.objects.filter(
            is_removed=False,
            schedule__is_removed=False,
            schedule__start_time__gte=start_dt,
            schedule__start_time__lte=end_dt,
        )
        .exclude(status=RESERVATION_STATUS_CANCELLED)
        .annotate(day=TruncDate("schedule__start_time"))
        .values("day")
        .annotate(total=Count("id"))
    )
    return {row["day"]: row["total"] for row in rows}


def _reservations_30d_series(by_day, start, end) -> dict:
    labels = []
    values = []
    cursor = start
    while cursor <= end:
        labels.append(cursor.isoformat())
        values.append(by_day.get(cursor, 0))
        cursor += timedelta(days=1)

    moving = []
    window = []
    for value in values:
        window.append(value)
        if len(window) > 7:
            window.pop(0)
        moving.append(round(sum(window) / len(window), 1))

    return {"labels": labels, "values": values, "moving_avg_7d": moving}


def _active_members_qs(today, created_on_or_before=None):
    qs = Member.objects.filter(is_removed=False, user__is_active=True, user__is_removed=False)
    if created_on_or_before is not None:
        qs = qs.filter(created__date__lte=created_on_or_before)

    with_wallet = qs.filter(
        Q(user__wallet__is_unlimited_membership_active=True)
        | Q(user__wallet__active_membership_end_date__gte=today)
    ).distinct()
    if with_wallet.exists():
        return with_wallet
    return qs


def _revenue_between(start, end) -> float:
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))
    total = PlanPurchase.objects.filter(created__gte=start_dt, created__lte=end_dt).aggregate(
        total=Sum("price_paid")
    )["total"]
    return float(total or 0)


def _convert_clp(amount_clp: float, clp_per_unit: float) -> float:
    if not clp_per_unit:
        return 0.0
    return round(float(amount_clp) / clp_per_unit, 2)


def _pct_change(current, previous) -> float | None:
    if previous in (None, 0):
        return None
    return round(100.0 * (current - previous) / previous, 1)


def _instructor_label(instructor) -> str:
    user = instructor.user
    first = (user.first_name or "").strip()
    last = (user.last_name or "").strip()
    if first and last:
        return f"{first} {last[0]}."
    return first or last or user.username


def _occupancy_by_instructor(schedules) -> list[dict]:
    buckets = defaultdict(lambda: {"occupied": 0, "capacity": 0})
    for schedule in schedules:
        key = _instructor_label(schedule.instructor)
        buckets[key]["occupied"] += schedule.occupied or 0
        buckets[key]["capacity"] += schedule.room.capacity or 0

    rows = []
    for name, totals in buckets.items():
        pct = _occupancy_pct(totals["occupied"], totals["capacity"])
        if pct is None:
            continue
        rows.append({"name": name, "occupancy": pct})
    rows.sort(key=lambda row: row["occupancy"], reverse=True)
    return rows


def _plan_mix(today, members_qs) -> list[dict]:
    now = timezone.make_aware(datetime.combine(today, time.max))
    members = members_qs.prefetch_related(
        Prefetch(
            "user__plan_purchases",
            queryset=PlanPurchase.objects.select_related("plan").order_by("-created"),
        )
    )
    counts = defaultdict(int)
    total = 0
    for member in members:
        total += 1
        plan_name = "Drop-in"
        for purchase in member.user.plan_purchases.all():
            if purchase.activated_since is None:
                continue
            if purchase.end and purchase.end < now:
                continue
            plan_name = _clean_plan_name(purchase.plan.name)
            break
        counts[plan_name] += 1

    if not total:
        return []

    rows = [
        {
            "plan": name,
            "count": count,
            "pct": round(100.0 * count / total, 1),
        }
        for name, count in sorted(counts.items(), key=lambda item: item[1], reverse=True)
    ]
    return rows


def _class_format(title: str) -> str:
    token = (title or "").strip().split(" ")[0].upper()
    if token in CLASS_FORMATS:
        return token
    return "OTRO"


def _demand_by_format(schedules) -> list[dict]:
    buckets = {fmt: {"occupied": 0, "capacity": 0} for fmt in CLASS_FORMATS}
    for schedule in schedules:
        fmt = _class_format(schedule.title)
        if fmt not in buckets:
            continue
        buckets[fmt]["occupied"] += schedule.occupied or 0
        buckets[fmt]["capacity"] += schedule.room.capacity or 0

    return [
        {
            "format": fmt,
            "occupancy": _occupancy_pct(totals["occupied"], totals["capacity"]) or 0,
        }
        for fmt, totals in buckets.items()
    ]


def _classes_vs_noshows(start, end) -> dict:
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))

    class_rows = (
        Schedule.objects.filter(
            is_removed=False,
            start_time__gte=start_dt,
            start_time__lte=end_dt,
        )
        .exclude(status__in=EXCLUDED_SCHEDULE_STATUSES)
        .annotate(day=TruncDate("start_time"))
        .values("day")
        .annotate(total=Count("id"))
    )
    classes_by_day = {row["day"]: row["total"] for row in class_rows}

    reservation_rows = (
        Reservation.objects.filter(
            is_removed=False,
            schedule__is_removed=False,
            schedule__start_time__gte=start_dt,
            schedule__start_time__lte=end_dt,
        )
        .exclude(status=RESERVATION_STATUS_CANCELLED)
        .annotate(day=TruncDate("schedule__start_time"))
        .values("day")
        .annotate(
            total=Count("id"),
            noshows=Count("id", filter=Q(status=RESERVATION_STATUS_MISSED)),
        )
    )
    reservations_by_day = {row["day"]: row for row in reservation_rows}

    labels = []
    classes = []
    noshows = []
    noshow_pct = []
    cursor = start
    while cursor <= end:
        labels.append(cursor.isoformat())
        classes.append(classes_by_day.get(cursor, 0))
        day_row = reservations_by_day.get(cursor)
        missed = day_row["noshows"] if day_row else 0
        total = day_row["total"] if day_row else 0
        noshows.append(missed)
        noshow_pct.append(round(100.0 * missed / total, 1) if total else 0)
        cursor += timedelta(days=1)

    return {
        "labels": labels,
        "classes": classes,
        "noshows": noshows,
        "noshow_pct": noshow_pct,
    }


def _schedule_vs_occupancy(schedules) -> list[dict]:
    points = []
    for schedule in schedules:
        pct = _occupancy_pct(schedule.occupied or 0, schedule.room.capacity or 0)
        if pct is None:
            continue
        local = timezone.localtime(schedule.start_time)
        hour = local.hour + (local.minute / 60.0)
        points.append(
            {
                "hour": round(hour, 2),
                "occupancy": pct,
                "title": schedule.title,
            }
        )
    return points


def _clean_plan_name(name: str | None) -> str:
    if not name:
        return "—"
    if name.startswith(DEMO_PLAN_PREFIX):
        return name[len(DEMO_PLAN_PREFIX) :]
    return name


def _wallet_commerce(today, revenue_start, last_30) -> dict:
    wallets = Wallet.objects.all()
    unlimited = wallets.filter(is_unlimited_membership_active=True).count()
    class_credits = wallets.aggregate(total=Sum("class_credits"))["total"] or 0
    guest_passes = wallets.aggregate(total=Sum("guest_pass_credits"))["total"] or 0

    purchases_7d_start = timezone.make_aware(datetime.combine(revenue_start, time.min))
    purchases_7d_end = timezone.make_aware(datetime.combine(today, time.max))
    purchases_7d = PlanPurchase.objects.filter(
        created__gte=purchases_7d_start, created__lte=purchases_7d_end
    ).count()

    month_start = timezone.make_aware(datetime.combine(last_30, time.min))
    month_end = purchases_7d_end
    month_purchases = (
        PlanPurchase.objects.filter(created__gte=month_start, created__lte=month_end)
        .select_related("plan", "user")
        .order_by("-created")
    )

    by_plan = defaultdict(lambda: {"count": 0, "revenue": 0.0})
    by_day_count = defaultdict(int)
    by_day_revenue = defaultdict(float)
    for purchase in month_purchases:
        plan_name = _clean_plan_name(purchase.plan.name)
        price = float(purchase.price_paid or 0)
        by_plan[plan_name]["count"] += 1
        by_plan[plan_name]["revenue"] += price
        day = timezone.localtime(purchase.created).date()
        by_day_count[day] += 1
        by_day_revenue[day] += price

    revenue_by_plan = [
        {
            "plan": name,
            "count": totals["count"],
            "revenue_clp": round(totals["revenue"], 2),
            "revenue_usd": _convert_clp(totals["revenue"], CLP_PER_USD),
            "revenue_mxn": _convert_clp(totals["revenue"], CLP_PER_MXN),
        }
        for name, totals in sorted(
            by_plan.items(), key=lambda item: item[1]["revenue"], reverse=True
        )
    ]

    labels = []
    counts = []
    revenues = []
    cursor = last_30
    while cursor <= today:
        labels.append(cursor.isoformat())
        counts.append(by_day_count.get(cursor, 0))
        revenues.append(round(by_day_revenue.get(cursor, 0.0), 2))
        cursor += timedelta(days=1)

    recent = []
    for purchase in month_purchases[:8]:
        user = purchase.user
        name = f"{(user.first_name or '').strip()} {(user.last_name or '').strip()}".strip()
        recent.append(
            {
                "id": str(purchase.id),
                "user_name": name or user.username or user.email,
                "plan_name": _clean_plan_name(purchase.plan.name),
                "price_paid": float(purchase.price_paid or 0),
                "created": purchase.created.isoformat() if purchase.created else None,
            }
        )

    return {
        "purchases_7d": purchases_7d,
        "unlimited_wallets": unlimited,
        "class_credits_outstanding": int(class_credits),
        "guest_passes_outstanding": int(guest_passes),
        "revenue_by_plan": revenue_by_plan,
        "purchases_30d": {"labels": labels, "counts": counts, "revenue_clp": revenues},
        "recent_purchases": recent,
    }
