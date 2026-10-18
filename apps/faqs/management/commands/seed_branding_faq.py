"""Seed the admin-only Branding (Marca) how-to FAQ section (CYC-432).

Idempotent: safe to run on every deploy from render_start.sh. The section is
``requires_staff`` so only superusers see it (same gate as Communications).
"""

from django.core.management.base import BaseCommand

from apps.faqs.models import FAQItem, Section

SECTION_SLUG = "marca-staff"

ITEMS = [
    (
        "¿Qué puedo personalizar en Marca?",
        "En **Estudio > Marca** defines la identidad del estudio: **nombre**, "
        "**logo (SVG)**, **colores** (principal, barra y fondos) y **tipografías** "
        "de títulos y textos. Los cambios se aplican a todo el sitio: página "
        "pública, área de socios y paneles de administración y coach.\n\n"
        "Solo administradores (superusuarios) pueden editarla.",
    ),
    (
        "¿Cómo subo el logo?",
        "Sube un archivo **.svg** de hasta 100 KB que incluya `viewBox`. Por "
        "seguridad el sistema limpia el archivo: se rechazan scripts, imágenes "
        "externas, hojas de estilo `<style>` y enlaces. Usa colores directos "
        "(atributo `fill`) en vez de clases CSS. Si el logo no se ve bien, "
        "expórtalo de nuevo como *SVG simple* desde tu herramienta de diseño.\n\n"
        "Para quitar el logo, usa **Quitar logo**; se mostrará el nombre del estudio.",
    ),
    (
        "¿Cómo elijo los colores?",
        "Usa el color principal para botones y acentos, el color de barra para "
        "la navegación oscura y los colores de fondo y texto para el cuerpo. "
        "El texto sobre el color principal se elige solo (blanco o negro). "
        "Si el contraste es menor a **4,5:1** verás una advertencia: conviene "
        "un color más oscuro o más claro para que se lea bien.",
    ),
    (
        "¿Qué tipografías están disponibles?",
        "Una lista de fuentes gratuitas de Google Fonts (por ejemplo Rubik, "
        "Inter, Montserrat, Poppins o Playfair Display). Se elige una para "
        "títulos y otra para textos.",
    ),
    (
        "¿Cómo vuelvo a la marca por defecto?",
        "Presiona **Restablecer** en la página Marca y confirma. Se restauran "
        "el nombre, colores y tipografías por defecto y se elimina el logo.",
    ),
]


class Command(BaseCommand):
    help = "Seed the admin-only Branding how-to FAQ section (idempotent)."

    def handle(self, *args, **options):
        section, created = Section.objects.get_or_create(
            slug=SECTION_SLUG,
            defaults={
                "name": "Marca",
                "description": "Guías del módulo Marca para administradores.",
                "order": 91,
                "requires_staff": True,
            },
        )
        if not section.requires_staff:
            section.requires_staff = True
            section.save(update_fields=["requires_staff"])
        created_items = 0
        for index, (question, answer) in enumerate(ITEMS, start=1):
            _, was_created = FAQItem.objects.get_or_create(
                section=section,
                question=question,
                defaults={"answer": answer, "order": index, "is_published": True},
            )
            created_items += int(was_created)
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_branding_faq: section {'created' if created else 'ok'}, "
                f"{created_items} new items."
            )
        )
