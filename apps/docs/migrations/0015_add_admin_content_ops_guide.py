from django.db import migrations


PAGE = {
    "slug": "admin-legales-y-docs",
    "title": "Publicar documentos legales y artículos de ayuda",
    "summary": "Gestiona términos, privacidad y artículos del centro de ayuda desde Django Admin.",
    "route": "#docs",
    "order": 2,
    "body": """
<h2>Dónde se gestionan</h2>
<p>Los documentos legales (términos y condiciones, aviso de privacidad) y los artículos del centro de ayuda se administran en <strong>Django Admin</strong> con una cuenta de superusuario. No tienen pantalla en PulseFit Admin.</p>

<h2>Publicar una versión legal</h2>
<p>En <strong>Legal documents</strong> crea un registro por tipo de documento y versión: define el contenido en Markdown, la fecha de vigencia y marca <em>is_published</em>. La API pública (<code>/api/legals/&lt;tipo&gt;/</code>) y la sección <a href="#legal/terms-and-conditions">Legal</a> muestran la versión publicada vigente; al publicar una versión nueva, despublica o elimina la anterior del mismo tipo.</p>

<h2>Editar artículos de ayuda</h2>
<p>En <strong>Secciones de documentación</strong> y <strong>Páginas de documentación</strong> controla título, resumen, contenido, orden y <em>is_published</em>. La audiencia define quién lo ve: Miembros y Plataforma son públicos; Staff solo para cuentas staff; Coach solo para instructores.</p>

<h2>Borrado suave</h2>
<p>Secciones, páginas y documentos legales usan borrado suave: al eliminarlos dejan de mostrarse pero pueden restaurarse desde Django Admin.</p>
""".strip(),
}


def add_guide(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")
    section, _ = DocSection.objects.update_or_create(
        slug="contenido-admin",
        defaults={
            "audience": "admin",
            "title": "Contenido",
            "order": 4,
            "is_published": True,
            "is_removed": False,
        },
    )
    DocPage.objects.update_or_create(
        section=section,
        slug=PAGE["slug"],
        defaults={
            "title": PAGE["title"],
            "summary": PAGE["summary"],
            "body": PAGE["body"],
            "order": PAGE["order"],
            "is_published": True,
            "related_app_route": PAGE["route"],
            "is_removed": False,
        },
    )


def remove_guide(apps, schema_editor):
    DocPage = apps.get_model("docs", "DocPage")
    DocPage.objects.filter(slug=PAGE["slug"]).delete()


class Migration(migrations.Migration):
    dependencies = [("docs", "0014_merge_referral_and_member_self_check_in")]
    operations = [migrations.RunPython(add_guide, remove_guide)]
