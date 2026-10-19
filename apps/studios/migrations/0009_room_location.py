"""Repoint Room from Studio to Location (CYC-456).

Rooms belong to a sede (Location); the brand studio is derived through
``location.studio``. Existing rooms are attached to their studio's first
location (created by 0008's backfill, one per studio).
"""

import django.db.models.deletion
from django.db import migrations, models


def backfill_room_locations(apps, schema_editor):
    Location = apps.get_model("studios", "Location")
    Room = apps.get_model("studios", "Room")
    Studio = apps.get_model("studios", "Studio")
    locations_by_studio = {}
    for location in Location.objects.order_by("created"):
        locations_by_studio.setdefault(location.studio_id, location)
    for studio in Studio.objects.all():
        if studio.id not in locations_by_studio:
            locations_by_studio[studio.id] = Location.objects.create(
                studio_id=studio.id,
                name=studio.name,
                address_id=studio.address_id,
                is_active=studio.is_active,
                opening_time=studio.opening_time,
                closing_time=studio.closing_time,
            )
    for room in Room.objects.all():
        location = locations_by_studio.get(room.studio_id)
        if location is not None:
            room.location_id = location.id
            room.save(update_fields=["location_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("studios", "0008_location_backfill"),
    ]

    operations = [
        migrations.AddField(
            model_name="room",
            name="location",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rooms",
                to="studios.location",
            ),
        ),
        migrations.RunPython(backfill_room_locations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="room",
            name="location",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="rooms",
                to="studios.location",
            ),
        ),
        migrations.RemoveField(
            model_name="room",
            name="studio",
        ),
    ]
