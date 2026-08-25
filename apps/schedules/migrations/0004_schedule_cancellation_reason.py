# Generated manually for class cancellation reason

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0003_alter_schedule_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="cancellation_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Optional reason shown to members when the class is cancelled.",
            ),
        ),
    ]
