from django.db import migrations


SECTIONS = (
    {
        "slug": "operacion-admin",
        "title": "Operación",
        "audience": "admin",
        "order": 1,
        "pages": (
            {
                "slug": "admin-perfil-staff",
                "title": "Mi perfil de staff",
                "summary": "Gestiona tus datos, contraseña y correo como integrante del staff.",
                "route": "#admin/profile",
                "order": 6,
                "body": """
<h2>Acceder a Mi perfil</h2>
<p>Con una cuenta de <strong>staff</strong>, abre <a href="#admin/profile">Mi perfil</a> desde Operación en PulseFit Admin.</p>

<h2>Datos que puedes editar</h2>
<p>Actualiza nombre, apellido, teléfono y género. El correo y el usuario se muestran como solo lectura; también verás tu último acceso y, si aplica, el badge de superuser.</p>

<h2>Accesos protegidos</h2>
<p>No puedes quitarte el rol Staff ni desactivar tu propia cuenta desde esta ficha.</p>

<h2>Contraseña y correo</h2>
<p>Para cambiar tu contraseña necesitas ingresar la actual y la nueva. Para cambiar el correo, solicita una confirmación: el correo actual se mantiene hasta que abras el enlace enviado a la nueva dirección.</p>
""".strip(),
            },
        ),
    },
    {
        "slug": "estudio-admin",
        "title": "Estudio",
        "audience": "admin",
        "order": 3,
        "pages": (
            {
                "slug": "admin-instructores",
                "title": "Gestionar instructores",
                "summary": "Lista, filtra y edita perfiles del equipo.",
                "route": "#admin/instructors",
                "order": 1,
                "body": """
<h2>Acceder a Instructores</h2>
<p>Con una cuenta de staff, abre <a href="#admin/instructors">Instructores</a> desde Estudio en PulseFit Admin.</p>

<h2>Listado y filtros</h2>
<p>La tabla muestra instructor, tagline, ubicación, verificación, estado y edición. Filtra por todos, verificados o sin verificar, y busca por nombre, correo, usuario, ubicación, redes o tagline.</p>

<h2>Editar un instructor</h2>
<p>Puedes actualizar datos personales, tagline, descripción, ubicación, fecha de inicio, sitio web, redes sociales, verificación, cuenta activa y playlists. El correo y usuario son solo lectura.</p>

<h2>Limitaciones</h2>
<p>PulseFit Admin no permite crear, eliminar ni cambiar la foto de un instructor. Crear y eliminar instructores se realiza en Django Admin con acceso de superusuario.</p>
""".strip(),
            },
            {
                "slug": "admin-usuarios",
                "title": "Gestionar usuarios",
                "summary": "Consulta cuentas, edita permisos y gestiona accesos.",
                "route": "#admin/users",
                "order": 2,
                "body": """
<h2>Acceder a Usuarios</h2>
<p>Con una cuenta de staff, abre <a href="#admin/users">Usuarios</a> desde Estudio en PulseFit Admin.</p>

<h2>Listado y roles</h2>
<p>Filtra por todos, staff o socios, y busca por nombre, correo, usuario o teléfono. Las filas muestran badges de Superuser, Staff o Socio.</p>

<h2>Editar un usuario</h2>
<p>Puedes actualizar nombre, apellido, teléfono, género, acceso Staff y estado de cuenta. El correo y usuario son solo lectura. Solo otro superuser puede editar una cuenta superuser.</p>

<h2>Gestiones de acceso</h2>
<p>Desde la ficha puedes enviar recuperación de contraseña o solicitar un cambio de correo con confirmación por enlace. No puedes quitarte el rol Staff ni desactivar tu propia cuenta.</p>

<h2>Limitaciones</h2>
<p>Crear y eliminar usuarios no está disponible en PulseFit Admin. El rol Superuser no se puede modificar desde esta interfaz.</p>
""".strip(),
            },
            {
                "slug": "admin-estudios-y-salas",
                "title": "Gestionar estudios y salas",
                "summary": "Crea ubicaciones, horarios, dirección y salas con capacidad.",
                "route": "#admin/studios",
                "order": 3,
                "body": """
<h2>Acceder a Estudios y salas</h2>
<p>Con una cuenta de staff, abre <a href="#admin/studios">Estudios y salas</a> desde Estudio en PulseFit Admin.</p>

<h2>Listado y filtros</h2>
<p>La tabla muestra estudio, dirección, horarios, cantidad de salas y estado. Filtra por activos o inactivos y busca por nombre, dirección o sala.</p>

<h2>Crear o editar un estudio</h2>
<p>El nombre es obligatorio. También puedes definir horario de apertura y cierre, dirección, coordenadas y estado activo. Tras crear un estudio, accedes a su ficha para gestionar salas.</p>

<h2>Gestionar salas</h2>
<p>Cada sala requiere nombre y capacidad. Puedes activarla o desactivarla, crearla desde <strong>Agregar sala</strong> y editarla desde la tabla. Su capacidad define el máximo de spots al programar y reservar clases.</p>

<h2>Limitaciones</h2>
<p>Esta pantalla no permite eliminar estudios ni salas.</p>
""".strip(),
            },
            {
                "slug": "admin-configuracion",
                "title": "Configuración del estudio",
                "summary": "Define la ventana de cancelación gratuita para socios.",
                "route": "#admin/settings",
                "order": 4,
                "body": """
<h2>Acceder a Configuración</h2>
<p>Abre <a href="#admin/settings">Configuración</a> desde Estudio en PulseFit Admin. Solo las cuentas de <strong>superusuario</strong> ven este ítem y pueden guardar cambios.</p>

<h2>Cancelación gratuita</h2>
<p>Define cuántas horas antes de una clase un socio puede cancelar sin perder crédito. El valor debe ser un entero entre 0 y 168; el valor por defecto es 2 horas.</p>

<h2>Impacto</h2>
<p>La política se aplica de inmediato a nuevas cancelaciones de socios y aparece en el correo de reserva confirmada. El staff puede cancelar reservas sin aplicar esta ventana.</p>

<h2>Limitaciones</h2>
<p>Las cuentas staff que no son superuser pueden consultar, pero no editar, esta configuración.</p>
""".strip(),
            },
        ),
    },
    {
        "slug": "contenido-admin",
        "title": "Contenido",
        "audience": "admin",
        "order": 4,
        "pages": (
            {
                "slug": "admin-faq",
                "title": "Gestionar FAQ",
                "summary": "Organiza secciones y preguntas de la página pública.",
                "route": "#admin/faq",
                "order": 1,
                "body": """
<h2>Acceder al FAQ</h2>
<p>Con una cuenta de staff, abre <a href="#admin/faq">FAQ</a> desde Contenido en PulseFit Admin.</p>

<h2>Listado y filtros</h2>
<p>Consulta secciones, preguntas y estado de publicación. Filtra por sección, publicación y texto de la pregunta.</p>

<h2>Secciones</h2>
<p>Crea o edita una sección con nombre, slug, orden y descripción. Si no indicas slug u orden, el sistema los genera. Los nombres y slugs no se pueden duplicar.</p>

<h2>Preguntas</h2>
<p>Selecciona una sección, escribe pregunta y respuesta en Markdown, define el orden y marca si está publicada. Solo las preguntas publicadas aparecen en <a href="#faq">Preguntas frecuentes</a>.</p>

<h2>Limitaciones</h2>
<p>No puedes eliminar secciones ni preguntas desde PulseFit Admin. Despublicar una pregunta la oculta del sitio público.</p>
""".strip(),
            },
        ),
    },
    {
        "slug": "panel-coach",
        "title": "Panel de instructor",
        "audience": "coach",
        "order": 1,
        "pages": (
            {
                "slug": "coach-clases-del-dia",
                "title": "Clases del día",
                "summary": "Revisa tus clases, ocupación y accesos rápidos al roster.",
                "route": "#coach/today",
                "order": 1,
                "body": """
<h2>Acceder al panel</h2>
<p>Inicia sesión con un perfil de instructor y abre <a href="#coach/today">Clases del día</a>. Las cuentas que no tienen perfil de coach no pueden acceder.</p>

<h2>Qué muestra</h2>
<p>La pantalla lista tus clases asignadas para hoy. No muestra clases canceladas ni clases de otros instructores.</p>

<h2>Estado y ocupación</h2>
<p>Cada tarjeta muestra título, hora, duración, sala, reservas frente a capacidad y estado: Próxima, Llena o Hecha.</p>

<h2>Acciones rápidas</h2>
<p>Usa <strong>Ver riders</strong> para abrir el roster o <strong>Playlist</strong> para abrir la playlist de la clase. Si no tienes clases, verás un mensaje informativo.</p>
""".strip(),
            },
            {
                "slug": "coach-horario-ical",
                "title": "Mi horario e iCal",
                "summary": "Consulta tu calendario semanal y exporta tus clases a iCal.",
                "route": "#coach/schedule",
                "order": 2,
                "body": """
<h2>Acceder a Mi horario</h2>
<p>Con perfil de instructor, abre <a href="#coach/schedule">Mi horario</a> desde el menú de PulseFit Coach.</p>

<h2>Vista semanal</h2>
<p>El calendario muestra tus clases de lunes a domingo. Navega con las flechas o el selector de fecha; también verás el total de clases y minutos de la semana.</p>

<h2>Ver riders</h2>
<p>Selecciona un bloque de clase o una próxima clase para abrir su roster. Las clases canceladas no aparecen.</p>

<h2>Exportar iCal</h2>
<p>Presiona <strong>Exportar iCal</strong> para descargar <code>pulsefit-coach.ics</code> con las clases de la semana visible. La descarga requiere una sesión activa y puedes importarla en calendarios compatibles.</p>
""".strip(),
            },
            {
                "slug": "coach-roster-check-in",
                "title": "Lista de riders y check-in",
                "summary": "Consulta el roster, registra asistencia e inicia una clase.",
                "route": "#coach/roster",
                "order": 3,
                "body": """
<h2>Acceder al roster</h2>
<p>Abre <a href="#coach/roster">Lista de riders</a> desde el menú o llega desde Clases del día y Mi horario. Solo puedes ver clases asignadas a ti.</p>

<h2>Qué riders aparecen</h2>
<p>El roster incluye reservas activas, asistentes y no-shows; las reservas canceladas no se muestran. Verás spot, nombre, primera clase y estado de check-in.</p>

<h2>Buscar y registrar check-in</h2>
<p>Busca por nombre o spot. Activa el interruptor para marcar <strong>Presente</strong> o desactívalo para volver a <strong>Esperando</strong>; los cambios se guardan al instante.</p>

<h2>Iniciar y exportar</h2>
<p>Usa <strong>Iniciar clase</strong> para confirmar el inicio operativo. <strong>Exportar lista</strong> descarga un CSV con spot, nombre, check-in y primera clase.</p>

<h2>Límites</h2>
<p>Esta pantalla no cancela reservas ni cambia spots. Para notas de setup de bicicleta o lesiones, usa <a href="#coach/notes">Notas de riders</a>.</p>
""".strip(),
            },
        ),
    },
)


def add_staff_and_coach_guides(apps, schema_editor):
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
        for page_data in section_data["pages"]:
            DocPage.objects.update_or_create(
                section=section,
                slug=page_data["slug"],
                defaults={
                    "title": page_data["title"],
                    "summary": page_data["summary"],
                    "body": page_data["body"],
                    "order": page_data["order"],
                    "is_published": True,
                    "related_app_route": page_data["route"],
                    "is_removed": False,
                },
            )


def remove_staff_and_coach_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    removable_section_slugs = {
        "estudio-admin",
        "contenido-admin",
        "panel-coach",
    }
    DocSection.objects.filter(slug__in=removable_section_slugs).delete()
    for section_data in SECTIONS:
        for page_data in section_data["pages"]:
            if section_data["slug"] == "operacion-admin":
                DocSection.objects.get(slug="operacion-admin").pages.filter(
                    slug=page_data["slug"]
                ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0005_add_admin_guides"),
    ]

    operations = [
        migrations.RunPython(add_staff_and_coach_guides, remove_staff_and_coach_guides),
    ]
