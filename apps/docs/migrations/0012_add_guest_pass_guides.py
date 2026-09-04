from django.db import migrations


PAGES = (
    (
        "invitar-con-pase-de-invitado",
        "Invitar con un pase de invitado",
        "Comparte una clase sin descontar tu pase hasta que tu invitado reserve.",
        "#wallet",
        """<h2>Invita desde tu billetera</h2><p>En <strong>Billetera</strong>, selecciona <strong>Invitar amigo</strong>, agrega su nombre, correo y un mensaje opcional. El pase queda emitido por 14 días.</p><h2>Uso y seguimiento</h2><p>El pase no se descuenta al enviar la invitación: se descuenta solo cuando tu invitado confirma una reserva. Consulta el historial para ver si fue emitido, reclamado, reservado o venció.</p><h2>Cancelaciones</h2><p>Si una reserva de invitado se cancela dentro de la política de cancelación, el pase vuelve automáticamente a tu billetera.</p>""",
    ),
    (
        "reservar-con-pase-de-invitado",
        "Reservar con un pase de invitado",
        "Reclama tu invitación, acepta el consentimiento y confirma tu reserva.",
        "#guest-pass",
        """<h2>Abre tu invitación</h2><p>Usa el enlace recibido, inicia sesión o crea tu cuenta con el mismo correo al que se envió el pase. Acepta el consentimiento informado para continuar.</p><h2>Confirma tu lugar</h2><p>Elige un spot y confirma. Si la clase se llenó, podrás sumarte a la lista de espera desde el horario.</p><h2>Tu privacidad</h2><p>Registramos la aceptación del consentimiento y el estado del pase para que el studio y quien te invitó puedan dar seguimiento a la reserva.</p>""",
    ),
)


def add_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")
    section, _ = DocSection.objects.update_or_create(
        slug="pases-de-invitado",
        defaults={
            "audience": "member",
            "title": "Pases de invitado",
            "order": 4,
            "is_published": True,
            "is_removed": False,
        },
    )
    for order, (slug, title, summary, route, body) in enumerate(PAGES, start=1):
        DocPage.objects.update_or_create(
            section=section,
            slug=slug,
            defaults={
                "title": title,
                "summary": summary,
                "body": body,
                "order": order,
                "related_app_route": route,
                "is_published": True,
                "is_removed": False,
            },
        )


def remove_guides(apps, schema_editor):
    apps.get_model("docs", "DocPage").objects.filter(slug__in=[page[0] for page in PAGES]).delete()


class Migration(migrations.Migration):
    dependencies = [("docs", "0011_merge_first_timer_and_favorite_alert_guides")]
    operations = [migrations.RunPython(add_guides, remove_guides)]
