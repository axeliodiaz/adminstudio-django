from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0012_emailchangerequest"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="injury_notes",
            field=models.TextField(
                blank=True,
                help_text="Optional information shared with the coach before a first class.",
            ),
        ),
    ]
