# CYC-6: marker for membership/pack expiry reminder emails.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("wallets", "0007_cyc79_hot_path_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="planpurchase",
            name="expiry_reminder_sent_at",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="Expiry Reminder Sent At"
            ),
        ),
    ]
