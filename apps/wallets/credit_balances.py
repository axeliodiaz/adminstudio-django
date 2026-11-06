"""Lazy valid-credit projections; the stored balance includes every unspent lot."""

from django.db.models import F, IntegerField, OuterRef, Subquery, Sum, Value
from django.db.models.functions import Coalesce, Greatest
from django.utils import timezone
from apps.wallets.models import ClassCreditLot


def with_available_credits(wallets, when=None):
    expired = (
        ClassCreditLot.objects.filter(
            wallet_id=OuterRef("pk"), expires_at__lt=when or timezone.now()
        )
        .order_by()
        .values("wallet_id")
        .annotate(total=Sum("remaining"))
        .values("total")
    )
    return wallets.annotate(
        valid_class_credits=Greatest(
            Value(0),
            F("class_credits") - Coalesce(Subquery(expired, output_field=IntegerField()), Value(0)),
        )
    )
