from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("schedules", "0005_scheduleinstructorsubstitution")]

    operations = [
        migrations.AddField(
            model_name="schedule",
            name="check_in_qr_version",
            field=models.PositiveIntegerField(
                default=1,
                help_text="Incremented to revoke previously generated class check-in QR tokens.",
            ),
        ),
    ]
