"""Give active studios the gold palette the live site already shows.

The StudioBranding default (studio=NULL) stays the new indigo palette for
future studios. The studios that exist today keep the exact gold look the
site had before Marca shipped, so releasing the branding feature does not
change how the production site or its emails look.
"""

from django.db import migrations

# The live PulseFit palette, taken from the production stylesheet.
GOLD_BRANDING = {
    "primary_color": "#C9A66B",
    "secondary_color": "#333333",
    "background_color": "#F5F5F5",
    "text_color": "#212121",
    "heading_font": "Rubik",
    "body_font": "Rubik",
}


def create_gold_branding(apps, schema_editor):
    Studio = apps.get_model("studios", "Studio")
    StudioBranding = apps.get_model("studios", "StudioBranding")
    branded = StudioBranding.objects.values_list("studio_id", flat=True)
    for studio in Studio.objects.filter(is_active=True).exclude(id__in=branded):
        StudioBranding.objects.create(studio=studio, name=studio.name, **GOLD_BRANDING)


class Migration(migrations.Migration):

    dependencies = [
        ("studios", "0006_studiobranding"),
    ]

    operations = [
        migrations.RunPython(create_gold_branding, migrations.RunPython.noop),
    ]
