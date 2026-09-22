"""Replace the Mexican-law privacy notice with one based on Chilean law (Ley 19.628)."""

import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def update_privacy_policy(apps, schema_editor):
    LegalDocument = apps.get_model("legal", "LegalDocument")
    fixture_path = Path(settings.BASE_DIR) / "apps" / "legal" / "fixtures" / "legal.json"
    entries = json.loads(fixture_path.read_text(encoding="utf-8"))
    fields = next(
        (
            entry["fields"]
            for entry in entries
            if entry.get("fields", {}).get("document_type") == "privacy_policy"
            and entry.get("fields", {}).get("language", "es") == "es"
        ),
        None,
    )
    if not fields:
        return
    document = (
        LegalDocument.objects.filter(
            document_type="privacy_policy",
            language="es",
            is_published=True,
            is_removed=False,
        )
        .order_by("-effective_date", "-order")
        .first()
    )
    if document is None or document.version == fields.get("version"):
        return
    document.title = fields.get("title", document.title)
    document.content = fields["content"]
    document.version = fields.get("version", document.version)
    if fields.get("effective_date"):
        document.effective_date = fields["effective_date"]
    document.save(update_fields=["title", "content", "version", "effective_date", "modified"])


class Migration(migrations.Migration):

    dependencies = [
        ("legal", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(update_privacy_policy, migrations.RunPython.noop),
    ]
