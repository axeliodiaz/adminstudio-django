from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("wallets", "0004_giftcard")]

    operations = [
        migrations.AddField(
            model_name="giftcard",
            name="delivered_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="giftcard",
            name="expiration_reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
