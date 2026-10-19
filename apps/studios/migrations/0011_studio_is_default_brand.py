"""Flag the site's brand studio for explicit branding resolution (CYC-457).

Branding lives on the brand Studio; the public site and Marca admin resolve
that brand row without a ``?studio=`` param. The flag replaces the
"exactly one active studio" heuristic with an explicit, admin-visible mark.
Defensive backfill: only when exactly one active studio exists (true in prod
after 0010 folded the demo studio into the brand).
"""

from django.db import migrations, models


def flag_default_brand(apps, schema_editor):
    Studio = apps.get_model("studios", "Studio")
    actives = list(Studio.objects.filter(is_active=True))
    if len(actives) == 1:
        actives[0].is_default_brand = True
        actives[0].save(update_fields=["is_default_brand"])


class Migration(migrations.Migration):

    dependencies = [
        ("studios", "0010_fold_demo_studio"),
    ]

    operations = [
        migrations.AddField(
            model_name="studio",
            name="is_default_brand",
            field=models.BooleanField(
                default=False,
                help_text="The site's brand studio: its branding row themes the public "
                "site and emails when no studio is specified (CYC-457).",
            ),
        ),
        migrations.RunPython(flag_default_brand, migrations.RunPython.noop),
    ]
