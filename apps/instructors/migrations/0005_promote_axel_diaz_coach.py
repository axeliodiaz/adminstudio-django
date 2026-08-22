from django.db import migrations


def noop(apps, schema_editor):
    """Coach access is an Instructor row in the DB, not a hardcoded user flag."""


class Migration(migrations.Migration):

    dependencies = [
        ("instructors", "0004_instructor_certifications_instructor_languages_and_more"),
        ("users", "0010_waitlist_and_auto_confirm"),
    ]

    operations = [
        migrations.RunPython(noop, migrations.RunPython.noop),
    ]
