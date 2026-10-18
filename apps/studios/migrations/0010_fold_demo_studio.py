"""Fold the demo studio into the brand studio (CYC-456).

Production carries two Studio rows for one brand ("PulseFit" and
"PulseFit Patio Andino (demo)"). Axel's restructure makes Studio the brand
and Location the sede: the demo studio's location moves under the brand
studio, its rooms follow automatically (rooms hang off locations since
0009), its branding row is dropped (brand-level branding lives on the brand
studio, CYC-457), report rows are repointed, and the demo Studio row is
soft-deleted.

Defensive: the fold runs only when exactly one demo studio (name contains
"(demo)", same marker as 0005) and exactly one other studio exist; any
other shape is left untouched.
"""

from django.db import migrations


def fold_demo_studio(apps, schema_editor):
    Studio = apps.get_model("studios", "Studio")
    Location = apps.get_model("studios", "Location")
    StudioBranding = apps.get_model("studios", "StudioBranding")
    DailyMetrics = apps.get_model("reports", "DailyMetrics")
    ClassMetrics = apps.get_model("reports", "ClassMetrics")

    demos = list(Studio.objects.filter(name__icontains="(demo)"))
    others = list(Studio.objects.exclude(name__icontains="(demo)"))
    if len(demos) != 1 or len(others) != 1:
        return
    demo, brand = demos[0], others[0]

    for location in Location.objects.filter(studio_id=demo.id):
        location.studio_id = brand.id
        # "PulseFit Patio Andino (demo)" -> "Patio Andino"
        name = location.name
        if name.startswith(brand.name):
            name = name[len(brand.name) :].strip()
        if name.endswith("(demo)"):
            name = name[: -len("(demo)")].strip()
        location.name = name or location.name
        location.save(update_fields=["studio_id", "name"])

    StudioBranding.objects.filter(studio_id=demo.id).delete()
    DailyMetrics.objects.filter(studio_id=demo.id).update(studio_id=brand.id)
    ClassMetrics.objects.filter(studio_id=demo.id).update(studio_id=brand.id)

    demo.is_active = False
    demo.is_removed = True  # soft delete: keeps the row for audit
    demo.save(update_fields=["is_active", "is_removed"])


class Migration(migrations.Migration):

    dependencies = [
        ("studios", "0009_room_location"),
        ("reports", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(fold_demo_studio, migrations.RunPython.noop),
    ]
