"""Versioned fixture pack layout and dump order."""

from pathlib import Path

from django.conf import settings

PACKS_ROOT = Path(settings.BASE_DIR) / "fixtures" / "packs"

# Foreign-key order. Each entry is dumped/loaded as its own file.
MODEL_LABELS = (
    "studios.address",
    "studios.studio",
    "studios.room",
    "users.user",
    "instructors.instructor",
    "members.member",
    "plans.benefit",
    "plans.plan",
    "plans.promocode",
    "wallets.wallet",
    "wallets.planpurchase",
    "schedules.schedule",
    "members.reservation",
    "members.waitlistentry",
    "coach.playlisttemplate",
    "coach.classplaylist",
    "coach.playlistsegment",
    "coach.playlisttrack",
    "coach.classrating",
    "notifications.notification",
    "faqs.section",
    "faqs.faqitem",
    "legal.legaldocument",
)
