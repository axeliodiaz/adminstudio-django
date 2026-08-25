# Generated manually for class-cancel + credit lifecycle

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("members", "0004_waitlist_and_auto_confirm"),
    ]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="cancellation_source",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Who cancelled: member, studio (staff), or schedule (class cancelled).",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="credit_charged",
            field=models.BooleanField(
                default=False,
                help_text="True when a class credit was deducted from the wallet for this reservation.",
            ),
        ),
    ]
