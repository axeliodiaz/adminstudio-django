from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("members", "0006_favorite_alerts")]

    operations = [
        migrations.AddField(
            model_name="reservation",
            name="attended_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="reservation",
            name="attendance_method",
            field=models.CharField(
                blank=True,
                default="",
                help_text="How attendance was recorded, for example manual, self, or qr.",
                max_length=20,
            ),
        ),
    ]
