from django.db import migrations


SECTION = {
    "slug": "regalos",
    "title": "Regalos y gift cards",
    "audience": "member",
    "order": 3,
    "pages": (
        (
            "comprar-y-enviar-regalo",
            "Comprar y enviar un regalo",
            "Compra un plan para otra persona y envíale un código de canje.",
            "#cart",
            """
<h2>Comprar un regalo</h2><p>Agrega el plan o pack al carrito y selecciona <strong>Es un regalo</strong>. Completa el nombre y correo de la persona destinataria y, si quieres, un mensaje personal y una fecha de envío.</p>
<h2>Después del pago</h2><p>El destinatario recibe un correo con un enlace de canje. Recibirás el comprobante de la compra. Cada unidad comprada genera un código individual y solo puede canjearse una vez.</p>
<h2>Vigencia y cambios</h2><p>Los códigos vencen según la fecha indicada en el correo. Si escribiste un correo incorrecto, contacta a soporte antes de que el código se canjee. Un regalo canjeado no se puede transferir ni reembolsar automáticamente.</p>""",
        ),
        (
            "canjear-regalo",
            "Canjear un código de regalo",
            "Activa en tu billetera la membresía o pack que te regalaron.",
            "#redeem",
            """
<h2>Canjear</h2><p>Abre el enlace recibido, inicia sesión o crea una cuenta y pega tu código. Al confirmar, el plan se activa en tu billetera y podrás usar sus créditos o beneficios.</p>
<h2>Validaciones</h2><p>Un código solo puede canjearse una vez, no puede canjearlo quien emitió el regalo y debe estar vigente. Si ya fue usado, venció o fue cancelado, la aplicación te mostrará el motivo.</p>
<h2>¿No recibiste el correo?</h2><p>Revisa spam y confirma con quien te lo envió que usó tu correo. Si persiste el problema, contacta a soporte con el nombre del emisor y la fecha de compra.</p>""",
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
    dependencies = [("docs", "0008_alter_docsection_audience")]
    operations = [migrations.RunPython(add_guides, remove_guides)]
