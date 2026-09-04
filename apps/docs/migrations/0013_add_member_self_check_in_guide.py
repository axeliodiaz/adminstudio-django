from django.db import migrations


SECTION_SLUG = "clases-y-horarios"
PAGE_SLUG = "confirmar-asistencia-a-una-clase"

PAGE_BODY = """
<h2>Confirma tu llegada</h2>
<p>Cuando tengas una reserva activa, puedes confirmar tu asistencia desde <a href="#my-reservations">Mis reservas</a>. Esta acción registra que llegaste al estudio.</p>

<h2>¿Cuándo está disponible?</h2>
<p>El botón <strong>Confirmar asistencia</strong> se habilita 15 minutos antes del inicio de la clase y se mantiene disponible hasta su hora de comienzo.</p>

<h2>Después de confirmar</h2>
<p>Verás el estado <strong>Asistencia confirmada</strong>. Tu asistencia se considera en tus estadísticas personales.</p>

<h2>Si no ves el botón</h2>
<p>La ventana de confirmación todavía no se abre, ya cerró o la clase fue cancelada. En ese caso, consulta con el staff o tu coach en el estudio.</p>
""".strip()


def add_member_self_check_in_guide(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")

    section = DocSection.objects.get(slug=SECTION_SLUG)
    DocPage.objects.update_or_create(
        section=section,
        slug=PAGE_SLUG,
        defaults={
            "title": "Cómo confirmar asistencia a una clase",
            "summary": "Registra tu llegada desde Mis reservas antes de que comience la clase.",
            "body": PAGE_BODY,
            "order": 3,
            "is_published": True,
            "related_app_route": "#my-reservations",
            "is_removed": False,
        },
    )


def remove_member_self_check_in_guide(apps, schema_editor):
    DocPage = apps.get_model("docs", "DocPage")
    DocPage.objects.filter(section__slug=SECTION_SLUG, slug=PAGE_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0012_add_guest_pass_guides"),
    ]

    operations = [
        migrations.RunPython(add_member_self_check_in_guide, remove_member_self_check_in_guide),
    ]
