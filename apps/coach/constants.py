from zoneinfo import ZoneInfo

from apps.members.constants import (
    RESERVATION_STATUS_ATTENDED,
    RESERVATION_STATUS_CANCELLED,
    RESERVATION_STATUS_MISSED,
    RESERVATION_STATUS_RESERVED,
)

COACH_TIMEZONE = ZoneInfo("America/Santiago")

ROSTER_STATUSES = (
    RESERVATION_STATUS_RESERVED,
    RESERVATION_STATUS_ATTENDED,
    RESERVATION_STATUS_MISSED,
)

OCCUPIED_STATUSES = (
    RESERVATION_STATUS_RESERVED,
    RESERVATION_STATUS_ATTENDED,
)

CLASS_STATUS_UPCOMING = "upcoming"
CLASS_STATUS_FULL = "full"
CLASS_STATUS_COMPLETED = "completed"

GENERIC_TIPS = (
    "Recuerda saludar por el nombre y revisar el ajuste de bike en los primeros 5 minutos.",
    "Mantén el cueing simple: cadencia, resistencia y postura en cada bloque.",
    "Cierra la clase con un cool-down de 3 minutos y un agradecimiento al grupo.",
)

MONTH_LABELS_ES = (
    "Ene",
    "Feb",
    "Mar",
    "Abr",
    "May",
    "Jun",
    "Jul",
    "Ago",
    "Sep",
    "Oct",
    "Nov",
    "Dic",
)

DEMO_USERNAME_PREFIX = "demo.coach."
DEMO_SHOWCASE_USERNAME = "tomasride"
DEMO_CLASS_DESCRIPTION = "demo.coach"
DEMO_EMAIL_DOMAIN = "pulsefit.cl"
INJURY_KEYWORDS = ("lesión", "lesion", "injury")
TIP_TITLE = "Tip del día"

NOT_COACH_DETAIL = "No tienes perfil de coach."
CLASS_NOT_FOUND_DETAIL = "Clase no encontrada."
RESERVATION_NOT_FOUND_DETAIL = "Reserva no encontrada."
