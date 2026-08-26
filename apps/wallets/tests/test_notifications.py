from decimal import Decimal
from uuid import UUID

import pytest

from apps.wallets.models import PlanPurchase
from apps.wallets.notifications import format_clp, purchase_folio, send_purchase_receipt_email


@pytest.mark.django_db
class TestPurchaseReceiptEmail:
    def test_sends_sketch_copy_and_wallet_link(self, mocker, user, plan):
        user.first_name = "María"
        user.save(update_fields=["first_name"])
        plan.name = "Pack 10 clases"
        plan.classes_included = 10
        plan.duration_days = 90
        plan.save(update_fields=["name", "classes_included", "duration_days"])
        purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("80000.00"),
            quantity=1,
            payment_method="webpay",
        )
        from django.utils import timezone

        purchase.activated_since = timezone.now().date()
        purchase.save()

        create_notification = mocker.patch("apps.wallets.notifications.create_notification")

        send_purchase_receipt_email(purchase)

        create_notification.assert_called_once()
        kwargs = create_notification.call_args.kwargs
        assert kwargs["recipient_list"] == [user]
        assert kwargs["subject"].startswith("Comprobante · Pack 10 clases · $80.000")
        html = kwargs["html_content"]
        assert "Pago recibido" in html
        assert "Gracias, María. Tu compra ya está activa en la billetera." in html
        assert "Pack 10 clases" in html
        assert "$80.000 CLP" in html
        assert "10 clases" in html
        assert "Webpay" in html
        assert "Ver mi billetera" in html
        assert "http://localhost:5173/#wallet" in html
        assert (
            "Este correo es tu comprobante. La boleta electrónica se envía por separado si aplica."
            in html
        )
        assert purchase_folio(purchase) in html

    def test_format_clp_uses_thousands_separator(self):
        assert format_clp(Decimal("80000")) == "$80.000 CLP"
        assert format_clp("99.99") == "$100 CLP"

    def test_folio_is_stable_for_purchase_id(self, user, plan):
        purchase = PlanPurchase.objects.create(
            user=user,
            plan=plan,
            price_paid=Decimal("10.00"),
        )
        first = purchase_folio(purchase)
        second = purchase_folio(purchase)
        assert first == second
        assert first.startswith("PF-")
        UUID(str(purchase.id))
