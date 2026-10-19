"""Introduce Location (sede) and mirror every Studio 1:1 (CYC-455).

Pure addition: no reader uses Location yet, so nothing changes in the API or
the site. Each Studio gets one Location copying its name, address, active
flag and hours. The PulseFit / Patio Andino merge into one brand with two
sedes lands together with the reader switch (CYC-456), where the visible
change is reported.
"""

import uuid

import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from django.db import migrations, models


def backfill_locations(apps, schema_editor):
    Studio = apps.get_model("studios", "Studio")
    Location = apps.get_model("studios", "Location")
    for studio in Studio.objects.all():
        Location.objects.get_or_create(
            studio_id=studio.id,
            name=studio.name,
            defaults={
                "address_id": studio.address_id,
                "is_active": studio.is_active,
                "opening_time": studio.opening_time,
                "closing_time": studio.closing_time,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("studios", "0007_active_studio_gold_branding"),
    ]

    operations = [
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    model_utils.fields.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
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
                ("is_removed", models.BooleanField(default=False)),
                ("name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=False)),
                ("opening_time", models.TimeField(blank=True, null=True)),
                ("closing_time", models.TimeField(blank=True, null=True)),
                (
                    "address",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="locations",
                        to="studios.address",
                    ),
                ),
                (
                    "studio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locations",
                        to="studios.studio",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.RunPython(backfill_locations, migrations.RunPython.noop),
    ]
