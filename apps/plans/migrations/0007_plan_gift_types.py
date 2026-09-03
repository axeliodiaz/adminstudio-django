from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("plans", "0006_promocode_and_purchase_fields")]

    operations = [
        migrations.AlterField(
            model_name="plan",
            name="type",
            field=models.CharField(
                choices=[
                    ("MEMBERSHIP", "Membership"),
                    ("PACKAGE", "Package"),
                    ("GIFT_CARD", "Gift card"),
                    ("GIFT_PACK", "Gift pack"),
                ],
                default="MEMBERSHIP",
                max_length=100,
            ),
        )
    ]
