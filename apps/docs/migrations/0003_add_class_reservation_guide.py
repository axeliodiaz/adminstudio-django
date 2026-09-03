from django.db import migrations


SECTION_SLUG = "clases-y-horarios"
PAGE_SLUG = "como-reservar-una-clase"

PAGE_BODY = """
<h2>Antes de reservar</h2>
<p>Inicia sesión y revisa que tengas créditos disponibles o una membresía activa. Cada reserva consume un crédito, excepto cuando tienes una membresía ilimitada activa.</p>

<h2>Elige una clase y tu spot</h2>
<p>Desde <a href="#classes">Clases</a>, abre la clase que quieres tomar. Verás el mapa de spots: los disponibles se pueden seleccionar y los que ya están ocupados no se pueden elegir.</p>
<p>Selecciona el número del spot que prefieras. Solo puedes tener una reserva por clase.</p>

<h2>Confirma tu reserva</h2>
<p>Presiona <strong>Confirmar reserva</strong>. Si el spot continúa disponible y cumples con los requisitos, la reserva se confirma y podrás verla en <a href="#my-reservations">Mis reservas</a>.</p>

<h2>¿La clase está llena?</h2>
<p>Si no quedan spots disponibles, únete a la lista de espera. Te avisaremos cuando se libere un cupo para que puedas continuar con tu reserva.</p>

<h2>Cambiar o cancelar tu spot</h2>
<p>Antes de la clase puedes volver a su detalle para elegir otro spot disponible y confirmar el cambio. También puedes cancelar tu reserva desde la misma pantalla o desde <a href="#my-reservations">Mis reservas</a>, según las condiciones de cancelación del estudio.</p>
""".strip()


def add_class_reservation_guide(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")

    section = DocSection.objects.get(slug=SECTION_SLUG)
    DocPage.objects.update_or_create(
        section=section,
        slug=PAGE_SLUG,
        defaults={
            "title": "Cómo reservar una clase y elegir tu spot",
            "summary": "Elige un spot disponible y confirma tu reserva con créditos o membresía.",
            "body": PAGE_BODY,
            "order": 2,
            "is_published": True,
            "related_app_route": "#classes",
            "is_removed": False,
        },
    )


def remove_class_reservation_guide(apps, schema_editor):
    DocPage = apps.get_model("docs", "DocPage")
    DocPage.objects.filter(section__slug=SECTION_SLUG, slug=PAGE_SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0002_add_classes_guide"),
    ]

    operations = [
        migrations.RunPython(add_class_reservation_guide, remove_class_reservation_guide),
    ]
