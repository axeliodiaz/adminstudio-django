import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0006_promocode_and_purchase_fields"),
        ("wallets", "0003_promocode_and_purchase_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="GiftCard",
            fields=[
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                (
                    "id",
                    model_utils.fields.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("code", models.CharField(editable=False, max_length=32, unique=True)),
                ("recipient_name", models.CharField(blank=True, max_length=150)),
                ("recipient_email", models.EmailField(blank=True, max_length=254)),
                ("message", models.TextField(blank=True, max_length=1000)),
                ("send_at", models.DateTimeField(blank=True, null=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("redeemed", "Redeemed"),
                            ("expired", "Expired"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="active",
                        max_length=16,
                    ),
                ),
                ("redeemed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "issuer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="issued_gift_cards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "plan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gift_cards",
                        to="plans.plan",
                    ),
                ),
                (
                    "purchase",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gift_cards",
                        to="wallets.planpurchase",
                    ),
                ),
                (
                    "redeemed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="redeemed_gift_cards",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "redemption_purchase",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="gift_redemption",
                        to="wallets.planpurchase",
                    ),
                ),
            ],
            options={"ordering": ["-created"]},
        ),
        migrations.AddIndex(
            model_name="giftcard",
            index=models.Index(
                fields=["status", "expires_at"], name="wallets_gif_status_9ed4c9_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="giftcard",
            index=models.Index(
                fields=["recipient_email", "status"], name="wallets_gif_recipie_c2614c_idx"
            ),
        ),
    ]
