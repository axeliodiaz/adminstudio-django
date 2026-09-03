from django.db import migrations


SECTION = {
    "slug": "primer-ride",
    "title": "Tu primer ride",
    "audience": "member",
    "order": 4,
    "pages": (
        (
            "prepara-tu-primera-clase",
            "Prepárate para tu primera clase",
            "Completa tu perfil, reserva tu clase y llega preparado a tu primer ride.",
            "#classes",
            """
<h2>1. Completa tu perfil</h2><p>Antes de reservar, agrega tu <strong>altura</strong>, tu <strong>talla de zapatilla</strong> y, si corresponde, lesiones o consideraciones que debamos conocer. Esta información ayuda a tu coach a prepararte mejor.</p>
<h2>2. Reserva tu primera clase</h2><p>Busca un horario que te acomode, elige tu spot y confirma la reserva. Tu coach verá que es tu primera clase para acompañarte con el ajuste de la bicicleta.</p>
<h2>3. Qué traer</h2><p>Llega <strong>10 minutos antes</strong> para conocer el studio y ajustar tu bicicleta. Trae una toalla y agua para mantenerte hidratado. Usa ropa cómoda; te ayudaremos con el resto.</p>
<h2>Después de tu clase</h2><p>Cuando termines tu primer ride, revisa los planes regulares disponibles para mantener tu ritmo. Tu progreso y reservas quedan disponibles en tu cuenta.</p>""",
        ),
    ),
}


def add_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")
    section, _ = DocSection.objects.update_or_create(
        slug=SECTION["slug"],
        defaults={
            "audience": SECTION["audience"],
            "title": SECTION["title"],
            "order": SECTION["order"],
            "is_published": True,
            "is_removed": False,
        },
    )
    for order, (slug, title, summary, route, body) in enumerate(SECTION["pages"], start=1):
        DocPage.objects.update_or_create(
            section=section,
            slug=slug,
            defaults={
                "title": title,
                "summary": summary,
                "body": body,
                "order": order,
                "is_published": True,
                "related_app_route": route,
                "is_removed": False,
            },
        )


def remove_guides(apps, schema_editor):
    DocPage = apps.get_model("docs", "DocPage")
    DocPage.objects.filter(slug__in=[page[0] for page in SECTION["pages"]]).delete()


class Migration(migrations.Migration):
    dependencies = [("docs", "0009_add_gift_card_guides")]

    operations = [migrations.RunPython(add_guides, remove_guides)]
