from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0007_plan_gift_types"),
    ]

    operations = [
        migrations.AddField(
            model_name="plan",
            name="is_first_timer",
            field=models.BooleanField(
                default=False,
                help_text="Available only to users who have never completed a plan purchase.",
            ),
        ),
    ]
