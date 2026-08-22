from django.db import migrations

from apps.instructors.axel_diaz_coach import ensure_axel_diaz_is_coach


def promote_axel_diaz(apps, schema_editor):
    User = apps.get_model("users", "User")
    Instructor = apps.get_model("instructors", "Instructor")
    ensure_axel_diaz_is_coach(User, Instructor)


class Migration(migrations.Migration):

    dependencies = [
        ("instructors", "0004_instructor_certifications_instructor_languages_and_more"),
        ("users", "0010_waitlist_and_auto_confirm"),
    ]

    operations = [
        migrations.RunPython(promote_axel_diaz, migrations.RunPython.noop),
    ]
