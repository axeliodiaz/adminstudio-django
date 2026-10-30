"""Seed missing admin-only People and base Inventory how-to guides (CYC-423).

Additive and idempotent: preserve existing editorial content and publication state.
The existing FAQ endpoint restricts requires_staff sections to superusers.
"""

from django.core.management.base import BaseCommand

from apps.faqs.models import FAQItem, Section

SECTIONS = (
    {
        "slug": "personas-staff",
        "name": "Personas",
        "order": 93,
        "items": (
            (
                "¿Cómo consulto coaches, staff y socios en Personas?",
                "Con una cuenta de administrador (superusuario), abre **Equipo > Personas**. "
                "El directorio reúne coaches, staff y socios; una persona puede tener más de "
                "un rol. Cada fila muestra nombre, email, roles, estado y fecha de registro. "
                "El estado indica si la cuenta está activa, no si tiene un plan vigente.",
            ),
            (
                "¿Cómo busco y filtro personas?",
                "Elige **Todos**, **Coaches**, **Staff** o **Socios** y busca por nombre o email. "
                "Envía la búsqueda con el botón de la lupa. Socios muestra personas que no "
                "son staff ni coaches. Los filtros se combinan; si no hay resultados, prueba "
                "quitar la búsqueda o volver a Todos. La paginación Anterior/Siguiente, cuando "
                "está disponible, conserva el filtro y la búsqueda; cambiar un filtro vuelve "
                "a la primera página.",
            ),
            (
                "¿Puedo configurar contratos o remuneraciones desde Personas?",
                "No. Personas es actualmente un directorio de consulta. No incluye edición "
                "de contratos, remuneraciones ni liquidaciones. Para administrar una cuenta "
                "usa **Estudio > Usuarios**; para datos de socios, **Operación > Socios**; "
                "para el perfil de un coach, **Estudio > Instructores**. Los permisos de "
                "cada pantalla se mantienen.",
            ),
        ),
    },
    {
        "slug": "inventario-staff",
        "name": "Inventario",
        "order": 94,
        "items": (
            (
                "¿Cómo registro proveedores y sus productos?",
                "En **Inventario > Proveedores**, completa nombre y los datos de contacto "
                "disponibles. Usa **Agregar producto** para registrar un nombre, precio y "
                "moneda de referencia (CLP, USD o EUR), plazo en días y notas. Deja precio "
                "o plazo vacío si no lo conoces. **Guardar proveedor** guarda la ficha; "
                "no envía mensajes ni crea una compra. Busca por nombre o contacto y usa "
                "**Editar** para cambiar la ficha. Quitar un producto del formulario elimina "
                "esa referencia al guardar; Cancelar descarta los cambios sin guardar.",
            ),
            (
                "¿Cómo consulto quién cambió el inventario?",
                "Abre **Inventario > Auditoría** con una cuenta de administrador. La lista "
                "muestra fecha, usuario, tipo de registro y creación o actualización. "
                "Expande **Ver antes y después** para revisar los valores. Solo incluye "
                "altas de categorías, ubicaciones y artículos, y altas o ediciones de "
                "proveedores realizadas en la API desde que se activó esta función. "
                "No reconstruye el pasado ni registra cambios directos en base de datos "
                "o Django Admin. No hay movimientos de stock o lavandería implementados. "
                "El historial es de consulta: no permite editar ni borrar eventos.",
            ),
            (
                "¿Cómo preparo categorías y ubicaciones del inventario?",
                "Como administrador (superusuario), abre **Inventario > Inventario**. "
                "En **Categorías**, escribe el nombre y una descripción opcional y pulsa "
                "**Agregar**. En **Ubicaciones**, indica nombre, tipo (**Sala** o **Bodega**) "
                "y descripción opcional. Estas ubicaciones son registros del inventario; "
                "no crean salas de clases ni spots de reserva.",
            ),
            (
                "¿Cómo registro un artículo y dónde lo encuentro?",
                "En **Artículos**, escribe el nombre y selecciona una categoría existente. "
                "Puedes asignar una ubicación o dejar **Sin asignar**, e indicar un spot "
                "y un identificador de referencia. Pulsa el botón **+** para guardar y "
                "revisa la fila en la lista. Si falta una categoría o ubicación, créala "
                "primero en su pestaña. El spot es una referencia de texto, no una "
                "asignación automática de bicicleta en reservas.",
            ),
            (
                "¿El inventario controla stock, consumos, lavandería o proveedores?",
                "Todavía no. La pantalla permite crear y consultar categorías, ubicaciones "
                "y artículos. No hay controles de stock mínimo, movimientos de consumo, "
                "rotación de lavandería ni pérdidas. Tampoco hay botones para editar o eliminar artículos "
                "desde esta pantalla. No registres un artículo esperando que cambie una "
                "cantidad de stock o dispare una compra.",
            ),
        ),
    },
)


class Command(BaseCommand):
    help = "Seed admin-only People and base Inventory how-to FAQ (additive, idempotent)."

    def handle(self, *args, **options):
        created_items = 0
        for data in SECTIONS:
            section, _ = Section.objects.get_or_create(
                slug=data["slug"],
                defaults={
                    "name": data["name"],
                    "description": f"Guías de {data['name']} para administradores.",
                    "order": data["order"],
                    "requires_staff": True,
                },
            )
            # Repair an accidentally public section without replacing its content.
            if not section.requires_staff:
                section.requires_staff = True
                section.save(update_fields=["requires_staff"])
            for index, (question, answer) in enumerate(data["items"], start=1):
                item, created = FAQItem.all_objects.get_or_create(
                    section=section,
                    question=question,
                    defaults={"answer": answer, "order": index, "is_published": True},
                )
                # Update only the exact previous seed text, never editorial changes.
                previous_answers = {
                    answer.replace(
                        "rotación de lavandería ni pérdidas. Tampoco hay botones",
                        "rotación de lavandería, pérdidas ni historial de auditoría de movimientos. Tampoco hay botones",
                    ),
                    answer.replace(
                        "rotación de lavandería ni pérdidas. Tampoco hay botones",
                        "rotación de lavandería, pérdidas, proveedores ni historial de auditoría de movimientos. Tampoco hay botones",
                    ),
                }
                if (
                    not created
                    and not item.is_removed
                    and item.answer != answer
                    and item.answer in previous_answers
                ):
                    item.answer = answer
                    item.save(update_fields=["answer"])
                created_items += int(created)
        self.stdout.write(
            self.style.SUCCESS(f"seed_people_inventory_faq: {created_items} new items.")
        )
