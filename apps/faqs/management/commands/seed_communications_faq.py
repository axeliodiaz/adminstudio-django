"""Seed the staff-only Communications how-to FAQ section (CYC-420).

Idempotent: safe to run on every deploy from render_start.sh. The section
is staff-only (``requires_staff``), so it never appears in the public FAQ.
"""

from django.core.management.base import BaseCommand

from apps.faqs.models import FAQItem, Section

SECTION_SLUG = "comunicaciones-staff"

ITEMS = [
    (
        "¿Cómo filtro una audiencia para un mensaje?",
        "En **Comunicaciones > Audiencia** arma el filtro con condiciones: "
        "sin visita en X días, pack por vencer en X días, nunca ha reservado, "
        "o tiene créditos de clases.\n\n"
        "- Agrupa condiciones con **Y** (todas se cumplen) u **O** (al menos una).\n"
        "- Presiona **Filtrar** para ver el conteo de personas y una muestra "
        "de la audiencia.\n\n"
        "El filtro solo incluye personas activas con email.",
    ),
    (
        "¿Cómo redacto un mensaje con variables?",
        "En **Comunicaciones > Redacción**:\n\n"
        "1. Elige el canal (email).\n"
        "2. Escribe el asunto y el mensaje.\n"
        "3. Inserta variables con los chips: nombre, primer nombre y créditos "
        "restantes se reemplazan por los datos de cada persona.\n"
        "4. Revisa la **vista previa**, que renderiza el mensaje para una "
        "persona de muestra de la última audiencia filtrada.\n\n"
        "Una variable desconocida hace fallar la validación en vez de "
        "renderizar mal.",
    ),
    (
        "¿Qué canales puedo usar para enviar?",
        "Por ahora solo **email** está habilitado. SMS y WhatsApp aparecen en "
        'el selector pero deshabilitados con el aviso "Aún no disponible".',
    ),
    (
        "¿Cómo hago seguimiento de los clicks de un enlace?",
        "En **Comunicaciones > Enlaces** crea un enlace con la URL de destino. "
        "El sistema genera una URL propia del estudio con un token único por "
        "destinatario: al hacer click se registra la visita (con IP "
        "anonimizada) y se redirige al destino.\n\n"
        "En el detalle de cada enlace ves el conteo de clicks y la fecha del "
        "primer y último click.",
    ),
    (
        "¿Cómo envío una campaña a la audiencia?",
        "El envío todavía no está disponible: falta definir el proveedor de "
        "email y el modelo de datos de campañas. Mientras tanto puedes dejar "
        "lista la audiencia, el mensaje y los enlaces tracked.",
    ),
]


class Command(BaseCommand):
    help = "Seed the staff-only Communications how-to FAQ section (idempotent)."

    def handle(self, *args, **options):
        section, created = Section.objects.get_or_create(
            slug=SECTION_SLUG,
            defaults={
                "name": "Comunicaciones",
                "description": "Guías del módulo de Comunicaciones para el equipo.",
                "order": 90,
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
                f"seed_communications_faq: section {'created' if created else 'ok'}, "
                f"{created_items} new items."
            )
        )
