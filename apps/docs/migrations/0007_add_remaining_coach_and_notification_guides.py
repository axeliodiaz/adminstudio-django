from django.db import migrations


SECTIONS = (
    {
        "slug": "panel-coach",
        "title": "Panel de instructor",
        "audience": "coach",
        "order": 1,
        "pages": (
            (
                "coach-iniciar-clase",
                "Iniciar una clase",
                "Inicia una clase desde el roster de riders.",
                "#coach/roster",
                """
<h2>Acceder</h2><p>Abre <a href="#coach/roster">Lista de riders</a> desde Clases del día o Mi horario. Solo puedes ver clases asignadas a tu perfil de instructor.</p>
<h2>Iniciar clase</h2><p>Presiona <strong>Iniciar clase</strong>. Esta acción confirma el inicio operativo y muestra el aviso de éxito.</p>
<h2>Antes y después</h2><p>Puedes buscar riders, registrar check-in y exportar la lista antes o después de iniciar. La acción no cambia reservas, check-ins ni playlist.</p>
<h2>Limitaciones</h2><p>No existe un estado “en curso”: una clase programada no cambia al iniciarla.</p>""",
            ),
            (
                "coach-notas-riders",
                "Notas de riders",
                "Consulta notas y registra el setup de bicicleta por rider.",
                "#coach/notes",
                """
<h2>Acceder</h2><p>Abre <a href="#coach/notes">Notas de riders</a> desde el panel Coach o selecciona una clase desde Clases del día.</p>
<h2>Información disponible</h2><p>Verás spot, nombre, setup de bici, notas del instructor y alertas de primera clase, setup pendiente o lesión activa.</p>
<h2>Guardar cambios</h2><p><strong>Guardar nota</strong> actualiza la nota de esa reserva. <strong>Guardar setup</strong> actualiza las medidas cycling del socio para preparar su bicicleta.</p>
<h2>Límites</h2><p>Solo puedes gestionar riders de tus clases. Para check-in usa <a href="#coach/roster">Lista de riders</a>.</p>""",
            ),
            (
                "coach-playlist",
                "Playlist de clase",
                "Consulta y edita la playlist de una clase asignada.",
                "#coach/playlist",
                """
<h2>Acceder</h2><p>Abre <a href="#coach/playlist">Playlist</a> desde el panel Coach o desde una clase del día.</p>
<h2>Editar</h2><p>Puedes seleccionar segmentos, añadir tracks y guardar la playlist. Al guardar se reemplaza la configuración de segmentos y tracks de esa clase.</p>
<h2>Plantillas</h2><p>Las plantillas guardadas se muestran como catálogo de nombres; actualmente no aplican contenido a la playlist.</p>
<h2>Limitaciones</h2><p>La integración con Apple Music y Spotify no está activa. Tampoco hay acciones para reordenar o eliminar tracks desde la interfaz.</p>""",
            ),
            (
                "coach-estadisticas",
                "Estadísticas del coach",
                "Revisa clases, ocupación, riders y valoraciones de los últimos seis meses.",
                "#coach/stats",
                """
<h2>Acceder</h2><p>Abre <a href="#coach/stats">Estadísticas</a> desde el menú de PulseFit Coach.</p>
<h2>Resumen</h2><p>Consulta clases impartidas, riders atendidos, ocupación media y valoración media, junto con tendencias mensuales.</p>
<h2>Clases recientes</h2><p>La tabla muestra hasta ocho clases pasadas con ocupación y valoración. Puedes descargar un CSV desde tu navegador.</p>
<h2>Alcance</h2><p>Incluye solo tus clases no canceladas. La interfaz muestra siempre los últimos seis meses.</p>""",
            ),
            (
                "coach-perfil",
                "Mi perfil de instructor",
                "Actualiza la información pública y contacto de tu perfil de coach.",
                "#coach/profile",
                """
<h2>Acceder</h2><p>Abre <a href="#coach/profile">Mi perfil</a> desde el menú de PulseFit Coach.</p>
<h2>Perfil público</h2><p>Actualiza nombre, apellido, biografía, tagline, especialidades, idiomas y certificaciones.</p>
<h2>Contacto</h2><p>Puedes actualizar teléfono e Instagram. El correo, usuario, foto, fecha como instructor y total de clases son solo lectura.</p>
<h2>Guardar</h2><p>Usa <strong>Guardar cambios</strong> para enviar la actualización o <strong>Cancelar</strong> para restaurar los datos cargados.</p>""",
            ),
        ),
    },
    {
        "slug": "plataforma",
        "title": "Plataforma",
        "audience": "platform",
        "order": 1,
        "pages": (
            (
                "emails-transaccionales",
                "Emails transaccionales",
                "Plantillas y disparadores de los correos automáticos del sistema.",
                "#docs",
                """
<h2>Plantillas implementadas</h2><p>El sistema envía correos de verificación, bienvenida, recuperación de contraseña, cambio de correo, reserva confirmada, clase cancelada, comprobante de pago y lista de espera.</p>
<h2>Disparadores</h2><p>Se generan por acciones de cuenta, reservas, cancelaciones de estudio, activación de compras y liberación de cupos. Cada correo incluye la ruta correspondiente en la aplicación cuando aplica.</p>
<h2>Entrega</h2><p>Los correos se crean en la cola interna y se entregan al correo del usuario. El envío de cambio de correo se dirige a la nueva dirección para confirmar el cambio.</p>
<h2>Limitaciones</h2><p>Solo está implementado el transporte de correo. La cancelación voluntaria de un socio y el cambio de instructor no envían correo. Los códigos de recuperación caducan en 5 minutos y los de verificación en 24 horas por defecto.</p>""",
            ),
            (
                "cola-de-notificaciones",
                "Cola de notificaciones",
                "Procesamiento, reintentos y administración de correos pendientes.",
                "#docs",
                """
<h2>Flujo</h2><p>Cada correo se registra como una notificación en cola. El sistema intenta enviarlo de inmediato y marca como enviado solo cuando el proveedor confirma éxito; los fallos permanecen pendientes para reintento.</p>
<h2>Reintentos</h2><p>Un nuevo envío intenta procesar toda la cola pendiente. También se puede ejecutar <code>python manage.py process_pending_notifications</code> o el cron <code>POST /api/notifications/flush-pending/</code>.</p>
<h2>Cron y proveedores</h2><p>El cron requiere <code>X-Cron-Token</code> igual a <code>NOTIFICATIONS_CRON_TOKEN</code>. Según la configuración, se usa Mailtrap en desarrollo, Resend cuando hay clave disponible o el servicio externo de respaldo.</p>
<h2>Administración y límites</h2><p>La cola se consulta en Django Admin y no tiene pantalla en PulseFit Admin. No hay límite de reintentos ni dead-letter queue; usuarios sin correo o envíos fallidos permanecen en cola.</p>""",
            ),
        ),
    },
)


def add_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")
    for section_data in SECTIONS:
        section, _ = DocSection.objects.update_or_create(
            slug=section_data["slug"],
            defaults={
                "audience": section_data["audience"],
                "title": section_data["title"],
                "order": section_data["order"],
                "is_published": True,
                "is_removed": False,
            },
        )
        for order, page_data in enumerate(section_data["pages"], start=4):
            slug, title, summary, route, body = page_data
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
    slugs = [page[0] for section in SECTIONS for page in section["pages"]]
    DocPage.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [("docs", "0006_add_staff_and_coach_guides")]
    operations = [migrations.RunPython(add_guides, remove_guides)]
