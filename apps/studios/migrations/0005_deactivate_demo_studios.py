"""Deactivate demo studios so their locations disappear from public output."""

from django.db import migrations


def deactivate_demo_studios(apps, schema_editor):
    Studio = apps.get_model("studios", "Studio")
    Studio.objects.filter(name__icontains="(demo)").update(is_active=False)


class Migration(migrations.Migration):

    dependencies = [
        ("studios", "0004_studiosettings"),
    ]

    operations = [
        migrations.RunPython(deactivate_demo_studios, migrations.RunPython.noop),
    ]
