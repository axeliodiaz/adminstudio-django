"""Seed the admin-only Reports (Reportes) how-to FAQ section (CYC-444).

Idempotent: safe to run on every deploy from render_start.sh. The section is
``requires_staff`` so only staff see it (same gate as Marca/Communications).
"""

from django.core.management.base import BaseCommand

from apps.faqs.models import FAQItem, Section

SECTION_SLUG = "reportes-staff"

ITEMS = [
    (
        "¿Qué encuentro en Reportes?",
        "En **Analítica > Reportes** (solo administradores) ves ocho reportes "
        "del estudio: **Asistencia**, **Ocupación**, **Ingresos**, "
        "**Retención**, **Lista de espera**, **Instructores**, **Promociones "
        "y referidos** y **Comunicaciones**. Cada uno se puede filtrar por "
        "período (desde / hasta).",
    ),
    (
        "¿Qué tan actualizados están los datos?",
        "Los reportes se guardan **pre-calculados** en tablas propias para que "
        "carguen rápido. Se actualizan solos con cada evento (una reserva, una "
        "compra, un click) y además en cada despliegue del sistema. Si quieres "
        "forzar el recálculo, usa el botón **Recalcular** dentro de Reportes.",
    ),
    (
        "¿De dónde salen los ingresos?",
        "De las compras de planes registradas en el sistema (precio pagado, en "
        "CLP), con desglose por plan y distinción entre compradores nuevos y "
        "recurrentes. Ojo: los **pagos online están desactivados**, así que los "
        "montos reflejan compras registradas, no cobros confirmados en una "
        "pasarela.",
    ),
    (
        "¿Cómo se calcula la retención?",
        "Con la asistencia real: un rider es **nuevo** en el período si su "
        "primera clase asistida cae dentro de él, y **recurrente** si ya había "
        "asistido antes. La **retención a 30 días** mide cuántos riders "
        "activos en los 30 días anteriores volvieron a asistir en los últimos "
        "30 días.",
    ),
    (
        "¿Qué reportes no están disponibles todavía?",
        "Los que necesitan datos que aún no existen en el sistema: cierre de "
        "caja y egresos (no hay POS ni gastos), deudas (los pagos están "
        "desactivados), registro horario y sueldos del staff, conversión de "
        "prospectos (no hay módulo de leads), tasas de entrega y lectura de "
        "notificaciones (solo hay envíos y clicks) y movimientos de inventario "
        "(pendiente en el módulo de inventario).",
    ),
]


class Command(BaseCommand):
    help = "Seed the admin-only Reports how-to FAQ section (idempotent)."

    def handle(self, *args, **options):
        section, created = Section.objects.get_or_create(
            slug=SECTION_SLUG,
            defaults={
                "name": "Reportes",
                "description": "Guías del módulo Reportes para administradores.",
                "order": 92,
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
                f"seed_reports_faq: section {'created' if created else 'ok'}, "
                f"{created_items} new items."
            )
        )
