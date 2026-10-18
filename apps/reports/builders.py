"""Read-only report builders over the precomputed tables (CYC-440).

Every payload comes from ``DailyMetrics`` / ``ClassMetrics`` only: no live
aggregates over operational tables. Date ranges are inclusive and capped.
"""

from datetime import timedelta

from django.utils import timezone

from apps.reports.models import ClassMetrics, DailyMetrics
from apps.reports.services import DEFAULT_RANGE_DAYS, MAX_RANGE_DAYS

CURRENCY = "CLP"

REPORT_CATALOG = [
    {
        "key": "attendance",
        "name": "Asistencia",
        "description": "Reservas, asistencias, ausencias y cancelaciones por día, con tasas de asistencia y no-show.",
        "limitations": None,
    },
    {
        "key": "occupancy",
        "name": "Ocupación",
        "description": "Ocupación de spots por día y las clases más y menos llenas del período.",
        "limitations": None,
    },
    {
        "key": "revenue",
        "name": "Ingresos",
        "description": "Ingresos por compras de planes por día, desglose por plan y compradores nuevos vs recurrentes.",
        "limitations": "Los pagos online están desactivados: los montos reflejan compras registradas, no cobros confirmados.",
    },
    {
        "key": "retention",
        "name": "Retención",
        "description": "Riders nuevos vs recurrentes y retención a 30 días, calculada desde la asistencia real.",
        "limitations": None,
    },
    {
        "key": "waitlist",
        "name": "Lista de espera",
        "description": "Entradas a lista de espera, conversiones a reserva y las clases con más demanda insatisfecha.",
        "limitations": None,
    },
    {
        "key": "instructors",
        "name": "Instructores",
        "description": "Clases dictadas, ocupación, no-show y rating promedio por instructor.",
        "limitations": "El rating solo existe para clases evaluadas; hoy lo cargan los datos demo.",
    },
    {
        "key": "promotions",
        "name": "Promociones y referidos",
        "description": "Uso de códigos promocionales, gift cards, pases de invitado y referidos.",
        "limitations": None,
    },
    {
        "key": "communications",
        "name": "Comunicaciones",
        "description": "Notificaciones enviadas y clicks en enlaces tracked por día.",
        "limitations": "No hay tracking de entrega ni apertura: solo envíos registrados y clicks.",
    },
]


def parse_range(params):
    """Inclusive [from, to] date range from query params, capped at MAX_RANGE_DAYS."""
    to_day = _parse_date(params.get("to")) or timezone.localdate()
    from_day = _parse_date(params.get("from")) or (to_day - timedelta(days=DEFAULT_RANGE_DAYS - 1))
    if from_day > to_day:
        from_day, to_day = to_day, from_day
    if (to_day - from_day).days + 1 > MAX_RANGE_DAYS:
        from_day = to_day - timedelta(days=MAX_RANGE_DAYS - 1)
    return from_day, to_day


def _parse_date(raw):
    if not raw:
        return None
    try:
        return timezone.datetime.strptime(raw, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _daily(from_day, to_day):
    return DailyMetrics.objects.filter(
        studio__isnull=True, date__gte=from_day, date__lte=to_day
    ).order_by("date")


def _classes(from_day, to_day):
    return ClassMetrics.objects.filter(
        studio__isnull=True, date__gte=from_day, date__lte=to_day, is_canceled=False
    )


def _pct(part, whole):
    return round(part / whole * 100, 1) if whole else 0.0


def build_attendance(from_day, to_day):
    rows = list(_daily(from_day, to_day))
    series = [
        {
            "date": row.date.isoformat(),
            "booked": row.reservations_booked,
            "attended": row.reservations_attended,
            "missed": row.reservations_missed,
            "cancelled": row.reservations_cancelled,
            "attendance_rate": _pct(row.reservations_attended, row.reservations_booked),
            "no_show_rate": _pct(row.reservations_missed, row.reservations_booked),
        }
        for row in rows
    ]
    totals = {
        "booked": sum(row.reservations_booked for row in rows),
        "attended": sum(row.reservations_attended for row in rows),
        "missed": sum(row.reservations_missed for row in rows),
        "cancelled": sum(row.reservations_cancelled for row in rows),
    }
    totals["attendance_rate"] = _pct(totals["attended"], totals["booked"])
    totals["no_show_rate"] = _pct(totals["missed"], totals["booked"])
    return {"series": series, "totals": totals}


def build_occupancy(from_day, to_day):
    rows = list(_daily(from_day, to_day))
    classes = list(
        _classes(from_day, to_day)
        .select_related("instructor__user")
        .order_by("-occupancy_rate", "-date")
    )

    def serialize_class(row):
        return {
            "schedule_id": str(row.schedule_id),
            "date": row.date.isoformat(),
            "title": row.title,
            "instructor": (
                row.instructor.user.get_full_name() or row.instructor.user.username
                if row.instructor_id
                else None
            ),
            "booked": row.booked,
            "capacity": row.capacity,
            "occupancy_rate": row.occupancy_rate,
            "rating": float(row.rating) if row.rating is not None else None,
        }

    fullest = [serialize_class(row) for row in classes[:5]]
    emptiest = [serialize_class(row) for row in sorted(classes, key=lambda r: r.occupancy_rate)[:5]]
    booked = sum(row.reservations_booked for row in rows)
    capacity = sum(row.spots_capacity for row in rows)
    return {
        "series": [
            {
                "date": row.date.isoformat(),
                "capacity": row.spots_capacity,
                "booked": row.reservations_booked,
                "occupancy_rate": row.occupancy_rate,
            }
            for row in rows
        ],
        "totals": {
            "capacity": capacity,
            "booked": booked,
            "occupancy_rate": _pct(booked, capacity),
            "classes": sum(row.classes_total for row in rows),
        },
        "fullest_classes": fullest,
        "emptiest_classes": emptiest,
    }


def build_revenue(from_day, to_day):
    rows = list(_daily(from_day, to_day))
    by_plan = {}
    for row in rows:
        for plan, data in (row.revenue_by_plan or {}).items():
            entry = by_plan.setdefault(plan, {"revenue": 0.0, "count": 0})
            entry["revenue"] += data.get("revenue", 0.0)
            entry["count"] += data.get("count", 0)
    totals = {
        "revenue": float(sum(row.revenue for row in rows)),
        "purchases": sum(row.purchases_count for row in rows),
        "first_time_buyers": sum(row.first_time_buyers for row in rows),
        "returning_buyers": sum(row.returning_buyers for row in rows),
        "discount_total": float(sum(row.discount_total for row in rows)),
    }
    return {
        "currency": CURRENCY,
        "series": [
            {
                "date": row.date.isoformat(),
                "revenue": float(row.revenue),
                "purchases": row.purchases_count,
                "first_time_buyers": row.first_time_buyers,
                "returning_buyers": row.returning_buyers,
            }
            for row in rows
        ],
        "totals": totals,
        "by_plan": sorted(
            ({"plan": plan, **data} for plan, data in by_plan.items()),
            key=lambda item: item["revenue"],
            reverse=True,
        ),
    }


def build_retention(from_day, to_day):
    def attendees(start, end):
        ids = set()
        for row in _daily(start, end):
            ids.update(row.attendee_ids or [])
        return ids

    period = attendees(from_day, to_day)
    before = attendees(from_day - timedelta(days=MAX_RANGE_DAYS), from_day - timedelta(days=1))
    new_riders = period - before
    returning_riders = period & before

    current_start = to_day - timedelta(days=29)
    previous_start = to_day - timedelta(days=59)
    current = attendees(current_start, to_day)
    previous = attendees(previous_start, current_start - timedelta(days=1))
    retained = previous & current
    return {
        "from": from_day.isoformat(),
        "to": to_day.isoformat(),
        "active_riders": len(period),
        "new_riders": len(new_riders),
        "returning_riders": len(returning_riders),
        "retention_30d": {
            "previous_active": len(previous),
            "retained": len(retained),
            "rate": _pct(len(retained), len(previous)),
        },
    }


def build_waitlist(from_day, to_day):
    rows = list(_daily(from_day, to_day))
    classes = list(
        _classes(from_day, to_day)
        .select_related("instructor__user")
        .order_by("-waitlist_count")[:10]
    )
    entries = sum(row.waitlist_entries for row in rows)
    converted = sum(row.waitlist_converted for row in rows)
    return {
        "totals": {
            "entries": entries,
            "converted": converted,
            "conversion_rate": _pct(converted, entries),
        },
        "series": [
            {
                "date": row.date.isoformat(),
                "entries": row.waitlist_entries,
                "converted": row.waitlist_converted,
            }
            for row in rows
        ],
        "classes": [
            {
                "schedule_id": str(row.schedule_id),
                "date": row.date.isoformat(),
                "title": row.title,
                "instructor": (
                    row.instructor.user.get_full_name() or row.instructor.user.username
                    if row.instructor_id
                    else None
                ),
                "waitlist_count": row.waitlist_count,
                "waitlist_converted": row.waitlist_converted,
            }
            for row in classes
        ],
    }


def build_instructors(from_day, to_day):
    by_instructor = {}
    for row in _classes(from_day, to_day).select_related("instructor__user"):
        key = str(row.instructor_id) if row.instructor_id else "sin-instructor"
        entry = by_instructor.setdefault(
            key,
            {
                "instructor": (
                    row.instructor.user.get_full_name() or row.instructor.user.username
                    if row.instructor_id
                    else "Sin instructor"
                ),
                "classes": 0,
                "capacity": 0,
                "booked": 0,
                "attended": 0,
                "missed": 0,
                "ratings": [],
                "ratings_count": 0,
            },
        )
        entry["classes"] += 1
        entry["capacity"] += row.capacity
        entry["booked"] += row.booked
        entry["attended"] += row.attended
        entry["missed"] += row.missed
        if row.rating is not None:
            entry["ratings"].append(float(row.rating))
            entry["ratings_count"] += row.rating_count
    instructors = []
    for entry in by_instructor.values():
        instructors.append(
            {
                "instructor": entry["instructor"],
                "classes": entry["classes"],
                "booked": entry["booked"],
                "attended": entry["attended"],
                "missed": entry["missed"],
                "occupancy_rate": _pct(entry["booked"], entry["capacity"]),
                "no_show_rate": _pct(entry["missed"], entry["booked"]),
                "rating_avg": (
                    round(sum(entry["ratings"]) / len(entry["ratings"]), 2)
                    if entry["ratings"]
                    else None
                ),
                "ratings_count": entry["ratings_count"],
            }
        )
    instructors.sort(key=lambda item: item["classes"], reverse=True)
    return {"instructors": instructors}


def build_promotions(from_day, to_day):
    rows = list(_daily(from_day, to_day))
    totals = {
        "promo_uses": sum(row.promo_uses for row in rows),
        "discount_total": float(sum(row.discount_total for row in rows)),
        "gift_cards_sold": sum(row.gift_cards_sold for row in rows),
        "gift_cards_redeemed": sum(row.gift_cards_redeemed for row in rows),
        "guest_passes_issued": sum(row.guest_passes_issued for row in rows),
        "guest_passes_claimed": sum(row.guest_passes_claimed for row in rows),
        "guest_passes_attended": sum(row.guest_passes_attended for row in rows),
        "referrals_signed_up": sum(row.referrals_signed_up for row in rows),
        "referrals_converted": sum(row.referrals_converted for row in rows),
    }
    return {
        "currency": CURRENCY,
        "totals": totals,
        "series": [
            {
                "date": row.date.isoformat(),
                "promo_uses": row.promo_uses,
                "discount_total": float(row.discount_total),
                "gift_cards_sold": row.gift_cards_sold,
                "guest_passes_issued": row.guest_passes_issued,
                "referrals_signed_up": row.referrals_signed_up,
            }
            for row in rows
        ],
    }


def build_communications(from_day, to_day):
    rows = list(_daily(from_day, to_day))
    totals = {
        "notifications_sent": sum(row.notifications_sent for row in rows),
        "link_clicks": sum(row.link_clicks for row in rows),
    }
    return {
        "totals": totals,
        "series": [
            {
                "date": row.date.isoformat(),
                "notifications_sent": row.notifications_sent,
                "link_clicks": row.link_clicks,
            }
            for row in rows
        ],
    }


REPORT_BUILDERS = {
    "attendance": build_attendance,
    "occupancy": build_occupancy,
    "revenue": build_revenue,
    "retention": build_retention,
    "waitlist": build_waitlist,
    "instructors": build_instructors,
    "promotions": build_promotions,
    "communications": build_communications,
}
