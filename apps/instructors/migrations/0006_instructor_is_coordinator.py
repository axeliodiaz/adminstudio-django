from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("instructors", "0005_promote_axel_diaz_coach"),
    ]

    operations = [
        migrations.AddField(
            model_name="instructor",
            name="is_coordinator",
            field=models.BooleanField(
                default=False,
                help_text="Coach Coordinator: can view the staff admin Dashboard.",
            ),
        ),
    ]
