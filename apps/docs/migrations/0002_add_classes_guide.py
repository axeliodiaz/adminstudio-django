from django.db import migrations


SECTION_SLUG = "clases-y-horarios"
PAGE_SLUG = "como-ver-clases-y-horarios"

PAGE_BODY = """
<h2>Consulta el calendario</h2>
<p>Abre <a href="#classes">Clases</a> desde el menú principal para ver los horarios disponibles. En computador se muestra una vista semanal; en móvil, una lista del día.</p>
<p>Usa el selector de fecha para cambiar el día o la semana que quieres revisar. También puedes filtrar el calendario por sala, instructor o tipo de clase.</p>

<h2>Revisa una clase</h2>
<p>Selecciona una clase del calendario para abrir su detalle. Allí encontrarás su horario, duración, instructor y sala, además de los spots disponibles.</p>

<h2>Reserva tu spot</h2>
<p>Inicia sesión y elige un spot disponible para confirmar tu reserva. Para reservar necesitas créditos o una membresía activa. Si ya tienes una reserva, puedes verla desde <a href="#my-reservations">Mis reservas</a>.</p>

<h2>Cuando una clase está llena</h2>
<p>Si no quedan spots, puedes unirte a la lista de espera. Cuando se libere un cupo, recibirás una notificación para continuar con la reserva.</p>
""".strip()


def add_classes_guide(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")

    section, _ = DocSection.objects.update_or_create(
        slug=SECTION_SLUG,
        defaults={
            "audience": "member",
            "title": "Clases y horarios",
            "order": 1,
            "is_published": True,
            "is_removed": False,
        },
    )
    DocPage.objects.update_or_create(
        section=section,
        slug=PAGE_SLUG,
        defaults={
            "title": "Cómo ver clases y horarios",
            "summary": "Consulta el calendario, revisa una clase y reserva tu spot.",
            "body": PAGE_BODY,
            "order": 1,
            "is_published": True,
            "related_app_route": "#classes",
            "is_removed": False,
        },
    )


def remove_classes_guide(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocSection.objects.filter(slug=SECTION_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_classes_guide, remove_classes_guide),
    ]
