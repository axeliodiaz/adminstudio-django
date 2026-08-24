from django.db import migrations, models
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_waitlist_and_auto_confirm"),
    ]

    operations = [
        migrations.CreateModel(
            name="LoadedFixturePack",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="created"
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now, editable=False, verbose_name="modified"
                    ),
                ),
                ("version", models.CharField(max_length=32, unique=True)),
                ("notes", models.TextField(blank=True, default="")),
            ],
            options={
                "ordering": ["-created"],
            },
        ),
    ]
