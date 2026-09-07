from django.db import migrations


def add_referral_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")

    member_section, _ = DocSection.objects.get_or_create(
        slug="planes-y-compras",
        defaults={
            "audience": "member",
            "title": "Planes y compras",
            "order": 2,
            "is_published": True,
        },
    )
    DocPage.objects.update_or_create(
        section=member_section,
        slug="programa-de-referidos",
        defaults={
            "title": "Invita y gana créditos",
            "summary": "Comparte tu enlace único y ambos reciben créditos tras la primera compra.",
            "related_app_route": "#wallet",
            "order": 5,
            "is_published": True,
            "is_removed": False,
            "body": """
<h2>Comparte tu enlace</h2>
<p>Desde <a href="#wallet">Billetera</a>, abre <strong>Invita y gana</strong> y copia tu enlace o compártelo por WhatsApp o correo. Cada enlace contiene un código único asociado a tu cuenta.</p>
<h2>Cómo se acredita la recompensa</h2>
<p>La persona invitada debe registrarse desde el enlace y completar su primera compra. Cuando la compra se activa, ambos reciben los créditos configurados para el programa.</p>
<h2>Seguimiento</h2>
<p>En Billetera puedes ver las invitaciones pendientes y las que ya recibieron recompensa. Un referido solo puede generar una recompensa y no puedes usar tu propio código.</p>
<h2>Límites</h2>
<p>El studio puede pausar el programa, desactivar o expirar códigos y limitar cuántas recompensas recibe cada referente durante un mes.</p>
""".strip(),
        },
    )

    admin_section, _ = DocSection.objects.get_or_create(
        slug="comercial-admin",
        defaults={
            "audience": "admin",
            "title": "Comercial",
            "order": 2,
            "is_published": True,
        },
    )
    DocPage.objects.update_or_create(
        section=admin_section,
        slug="admin-programa-de-referidos",
        defaults={
            "title": "Auditar el programa de referidos",
            "summary": "Consulta conversiones, recompensas y referentes con mejor desempeño.",
            "related_app_route": "#admin/referrals",
            "order": 4,
            "is_published": True,
            "is_removed": False,
            "body": """
<h2>Dashboard</h2>
<p>En PulseFit Admin, abre <a href="#admin/referrals">Programa de referidos</a>. El resumen muestra clics, altas atribuidas, recompensas entregadas y créditos otorgados.</p>
<h2>Auditoría</h2>
<p>La tabla conserva el referente, referido, estado, fechas de alta, conversión y recompensa, y los créditos entregados a cada parte. Para una revisión detallada usa también Django Admin.</p>
<h2>Configuración</h2>
<p>Un superusuario puede administrar el programa en Django Admin: activarlo o pausarlo, definir créditos para referente y referido, aplicar el límite mensual, o desactivar y expirar códigos.</p>
""".strip(),
        },
    )


def remove_referral_guides(apps, schema_editor):
    DocPage = apps.get_model("docs", "DocPage")
    DocPage.objects.filter(
        slug__in=("programa-de-referidos", "admin-programa-de-referidos")
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("docs", "0008_alter_docsection_audience")]

    operations = [migrations.RunPython(add_referral_guides, remove_referral_guides)]
