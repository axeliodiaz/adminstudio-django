from django.db import migrations


FAVORITES_BODY = """
<h2>Favoritos y alertas por email</h2><p>Guarda instructores, bloques horarios y spots favoritos desde tu perfil. Las alertas se envían únicamente por email cuando se publica una clase que coincide con un instructor u horario favorito, o cuando queda libre un spot favorito.</p>
<h2>Disponibilidad y lista de espera</h2><p>Una alerta no reserva ni garantiza un cupo. Si tienes una reserva o estás en la lista de espera de esa clase, no recibirás esta alerta. La lista de espera siempre tiene prioridad cuando se libera un spot.</p>
<h2>Preferencias</h2><p>Puedes desactivar las alertas por email o configurar horas de silencio. Las horas se interpretan en la zona horaria configurada por la plataforma porque aún no guardamos una zona horaria individual. Un inicio y fin iguales desactivan el período de silencio.</p>
<h2>Límites</h2><p>Se envían como máximo 5 alertas de favoritos por socio y día. No hay recordatorios programados ni reintentos automáticos para estas alertas; revisa spam si no recibes un correo.</p>"""


def add_guide(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")
    section, _ = DocSection.objects.update_or_create(
        slug="mi-cuenta",
        defaults={
            "audience": "member",
            "title": "Mi cuenta",
            "order": 4,
            "is_published": True,
            "is_removed": False,
        },
    )
    DocPage.objects.update_or_create(
        section=section,
        slug="favoritos-y-alertas",
        defaults={
            "title": "Favoritos y alertas",
            "summary": "Configura favoritos y recibe alertas de disponibilidad por email.",
            "body": FAVORITES_BODY,
            "order": 1,
            "is_published": True,
            "related_app_route": "#docs",
            "is_removed": False,
        },
    )
    DocPage.objects.filter(slug="cola-de-notificaciones").update(
        body="""<h2>Flujo</h2><p>Los emails transaccionales se registran como notificaciones pendientes y se intentan enviar cuando se crean. Los fallos quedan pendientes para un reintento posterior de la cola.</p><h2>Reintentos</h2><p>La cola general puede procesarse con <code>python manage.py process_pending_notifications</code> o <code>POST /api/notifications/flush-pending/</code>. Las alertas de favoritos son distintas: se disparan solo por eventos y no usan cron, recordatorios ni reintentos programados.</p><h2>Administración</h2><p>La cola se consulta en Django Admin. Usuarios sin correo o envíos fallidos pueden permanecer pendientes.</p>"""
    )


def remove_guide(apps, schema_editor):
    apps.get_model("docs", "DocPage").objects.filter(slug="favoritos-y-alertas").delete()


class Migration(migrations.Migration):
    dependencies = [("docs", "0009_add_gift_card_guides")]
    operations = [migrations.RunPython(add_guide, remove_guide)]
