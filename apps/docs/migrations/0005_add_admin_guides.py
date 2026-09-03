from django.db import migrations


SECTIONS = (
    {
        "slug": "operacion-admin",
        "title": "Operación",
        "order": 1,
        "pages": (
            {
                "slug": "admin-dashboard",
                "title": "Admin dashboard",
                "summary": "Métricas operativas de ocupación, reservas, socios e ingresos.",
                "route": "#admin/dashboard",
                "order": 1,
                "body": """
<h2>Acceder al dashboard</h2>
<p>Inicia sesión con una cuenta de <strong>staff</strong> y abre <a href="#admin/dashboard">Dashboard</a> desde Operación en PulseFit Admin. Las cuentas sin permisos de staff no pueden acceder al panel.</p>

<h2>Elegir el período</h2>
<p>Usa el selector para revisar los últimos 7, 14, 30, 60 o 90 días. La preferencia queda guardada en el navegador.</p>

<h2>KPIs principales</h2>
<p>El dashboard muestra ocupación semanal, reservas de hoy, socios activos e ingresos del período. También incluye compras del período, membresías ilimitadas activas, créditos y pases de invitado pendientes.</p>

<h2>Gráficos</h2>
<p>Revisa reservas diarias, ocupación por instructor, compras e ingresos, ingresos por plan, mix de planes, demanda por formato, no-shows y ocupación por horario.</p>

<h2>Compras recientes</h2>
<p>La tabla muestra socio, plan, monto y fecha. Usa <strong>Ir a Billeteras y compras</strong> para consultar el detalle de créditos y compras.</p>
""".strip(),
            },
            {
                "slug": "admin-horarios",
                "title": "Gestionar horarios",
                "summary": "Crea, edita, duplica y cancela clases del calendario semanal.",
                "route": "#admin/schedule",
                "order": 2,
                "body": """
<h2>Acceder a Horarios</h2>
<p>Con una cuenta de staff, abre <a href="#admin/schedule">Horarios</a> desde Operación en PulseFit Admin.</p>

<h2>Calendario y filtros</h2>
<p>Consulta la semana actual y usa las flechas, el selector de fecha o <strong>Hoy</strong> para navegar. Filtra por estado, instructor o sala, y busca por nombre de clase.</p>

<h2>Crear una clase</h2>
<p>Selecciona un espacio vacío o presiona <strong>Nueva clase</strong>. Debes indicar título, inicio, duración, instructor y sala; también puedes añadir descripción, estado y repetición semanal.</p>
<p>Las duraciones disponibles son 30, 45, 50 o 60 minutos. Puedes repetir una nueva clase por 2, 4, 6, 8 o 12 semanas.</p>

<h2>Editar, duplicar o eliminar</h2>
<p>Selecciona una clase para editarla. <strong>Duplicar +7 días</strong> crea una nueva clase con la misma información una semana después. No puedes eliminar una clase con reservas activas.</p>

<h2>Cancelar una clase</h2>
<p>Cambia su estado a <strong>Cancelada</strong> e indica un motivo opcional. Al confirmar, se cancelan las reservas activas, se devuelven créditos, se notifica a los socios y se expira su lista de espera.</p>

<h2>Cambiar instructor</h2>
<p>Puedes cambiar el instructor en el formulario, pero esta acción no envía una notificación a los socios reservados.</p>
""".strip(),
            },
            {
                "slug": "admin-reservas",
                "title": "Gestionar reservas",
                "summary": "Consulta, crea, cancela reservas y cambia spots desde el panel.",
                "route": "#admin/reservations",
                "order": 3,
                "body": """
<h2>Acceder a Reservas</h2>
<p>Con una cuenta de staff, abre <a href="#admin/reservations">Reservas</a> desde Operación en PulseFit Admin.</p>

<h2>Lista y filtros</h2>
<p>La tabla muestra fecha, clase, socio, spot, sala, instructor, estado y acciones. Filtra por estado o semana y busca por correo del socio o nombre de clase.</p>
<p>Si llegas desde una clase con filtro, verás solo sus reservas y podrás quitarlo con <strong>Quitar filtro de clase</strong>.</p>

<h2>Crear una reserva</h2>
<p>Presiona <strong>Nueva reserva</strong> y selecciona socio, clase y spot. Las notas son opcionales.</p>
<p>El sistema valida que el spot esté libre y que el socio no tenga otra reserva para esa clase. Consume un crédito, salvo que el socio tenga membresía ilimitada activa, y envía un correo de confirmación.</p>

<h2>Cambiar spot</h2>
<p>En una reserva activa, edita el número de spot y confirma el cambio. El nuevo spot debe estar dentro de la capacidad de la sala y estar disponible.</p>

<h2>Cancelar una reserva</h2>
<p>El staff puede cancelar una reserva activa sin aplicar la ventana de cancelación gratuita del socio. Si correspondía, el crédito se devuelve y el cupo puede ofrecerse a la lista de espera.</p>

<h2>Asistencia</h2>
<p>Usa la acción <strong>Asistencia</strong> para abrir el roster de esa clase y registrar asistentes o no-shows.</p>
""".strip(),
            },
            {
                "slug": "asistencia",
                "title": "Asistencia",
                "summary": "Marca quién asistió a cada clase, incluso después de que ocurrió.",
                "route": "#admin/attendance",
                "order": 4,
                "body": """
<h2>Acceder a Asistencia</h2>
<p>Inicia sesión con una cuenta de staff y abre <a href="#admin/attendance">Asistencia</a> desde Operación en PulseFit Admin.</p>

<h2>Elegir el día</h2>
<p>Usa las flechas, el selector de fecha o <strong>Hoy</strong> para navegar. El listado excluye borradores y clases canceladas.</p>

<h2>Clases del día</h2>
<p>Cada clase muestra título, horario, duración, instructor, sala y el conteo de asistencias frente a reservas. Selecciona una clase para abrir su roster.</p>

<h2>Marcar la asistencia</h2>
<p>Para cada reserva puedes seleccionar <strong>Sí</strong> (Asistió), <strong>No</strong> (No show) o <strong>Pendiente</strong>. Puedes actualizar estos estados incluso después de que termine la clase.</p>

<h2>Limitaciones</h2>
<p>Las reservas canceladas no aparecen en el roster ni se pueden marcar. Esta pantalla no permite cancelar reservas ni cambiar spots; usa <a href="#admin/reservations">Reservas</a> para esas acciones.</p>
""".strip(),
            },
            {
                "slug": "admin-socios",
                "title": "Gestionar socios",
                "summary": "Lista, filtra, crea y edita miembros del estudio.",
                "route": "#admin/members",
                "order": 5,
                "body": """
<h2>Acceder a Socios</h2>
<p>Con una cuenta de staff, abre <a href="#admin/members">Socios</a> desde Operación en PulseFit Admin.</p>

<h2>Listado y filtros</h2>
<p>Filtra por socios activos o inactivos. Usa <strong>Buscar socio</strong> para buscar por nombre, correo, usuario o teléfono.</p>
<p>La tabla incluye datos de contacto, género, créditos, total de reservas, último acceso y estado de la cuenta.</p>

<h2>Crear un socio</h2>
<p>Presiona <strong>Nuevo socio</strong> y completa correo, contraseña inicial, nombre, apellido y teléfono. Después de crear la cuenta, podrás abrir su ficha.</p>

<h2>Editar un socio</h2>
<p>En la ficha puedes actualizar nombre, apellido, teléfono, género y si la cuenta está activa. El correo es de solo lectura en este formulario.</p>

<h2>Gestiones de cuenta</h2>
<p>Desde la ficha puedes enviar una recuperación de contraseña al correo actual o solicitar un cambio de correo. El nuevo correo no se aplica hasta que la persona confirme el enlace recibido.</p>

<h2>Estadísticas</h2>
<p>Usa <strong>Estadísticas</strong> para ver la actividad individual del socio, como horas en bici, coaches favoritos y avance del pack.</p>
""".strip(),
            },
        ),
    },
    {
        "slug": "comercial-admin",
        "title": "Comercial",
        "order": 2,
        "pages": (
            {
                "slug": "billeteras-y-compras",
                "title": "Billeteras y compras",
                "summary": "Consulta créditos, membresías activas e historial de compras de planes.",
                "route": "#admin/wallets",
                "order": 1,
                "body": """
<h2>Acceder a Billeteras y compras</h2>
<p>Inicia sesión con una cuenta de staff y abre <a href="#admin/wallets">Billeteras y compras</a> desde Comercial en PulseFit Admin.</p>

<h2>Dos vistas</h2>
<p>Alterna entre <strong>Billeteras</strong>, para revisar saldos y beneficios actuales, y <strong>Compras de planes</strong>, para consultar el historial comercial.</p>

<h2>Billeteras</h2>
<p>Filtra por todas, activas o vencidas y busca por nombre, correo o usuario. La tabla muestra plan activo, créditos de clase, pases de invitado, fecha de vencimiento y beneficios.</p>

<h2>Compras de planes</h2>
<p>Filtra por membresías o paquetes. Cada registro muestra usuario, plan, tipo, precio pagado, activación, vigencia y fecha de creación.</p>

<h2>Limitaciones</h2>
<p>Esta pantalla es solo de consulta: no permite editar créditos, activar compras, reembolsar ni procesar pagos. El historial muestra hasta las 500 compras más recientes.</p>
""".strip(),
            },
            {
                "slug": "gestionar-planes-y-beneficios",
                "title": "Gestionar planes y beneficios",
                "summary": "Crea y edita membresías, paquetes, precios y beneficios asociados.",
                "route": "#admin/plans",
                "order": 2,
                "body": """
<h2>Acceso</h2>
<p>Entra a <a href="#admin/plans">Planes y beneficios</a> desde Comercial en PulseFit Admin. Necesitas una cuenta de staff.</p>

<h2>Listado de planes</h2>
<p>Filtra por tipo (membresía o paquete), estado y búsqueda por nombre o beneficio. La tabla muestra nombre, tipo, precio, duración, clases incluidas, estado y etiquetas Popular o Destacado.</p>

<h2>Crear o editar un plan</h2>
<p>Usa <strong>Nuevo plan</strong> para indicar nombre, tipo, precio en CLP, duración, clases incluidas, pases de invitado, estado, popularidad, destacado y beneficios asociados.</p>
<p>Solo los planes activos aparecen en <a href="#pricing">Planes y Membresías</a>. Un plan nuevo se crea como inactivo por defecto.</p>

<h2>Beneficios</h2>
<p>En PulseFit Admin puedes listar y asignar beneficios a un plan. Para crear o editar un beneficio debes usar Django Admin con acceso de superusuario.</p>

<h2>Impacto en socios</h2>
<p>Las compras activadas otorgan créditos o membresía en la billetera. Cambiar el precio o beneficios de un plan no modifica las compras ya realizadas.</p>
""".strip(),
            },
            {
                "slug": "gestionar-codigos-promocionales",
                "title": "Gestionar códigos promocionales",
                "summary": "Crea códigos de descuento con vigencia y tipo porcentaje o monto fijo.",
                "route": "#admin/promo-codes",
                "order": 3,
                "body": """
<h2>Acceso</h2>
<p>Entra a <a href="#admin/promo-codes">Códigos promocionales</a> desde Comercial en PulseFit Admin. Requiere una cuenta de staff.</p>

<h2>Listado de códigos</h2>
<p>La tabla muestra código, descripción, descuento, vigencia, estado y acción de edición. Filtra por activo o inactivo y busca por código o descripción.</p>

<h2>Crear o editar</h2>
<p>Indica el código, una descripción opcional, tipo de descuento, valor, estado y fechas de inicio y término. Los códigos se guardan en mayúsculas.</p>
<p>El descuento puede ser un porcentaje (máximo 100) o un monto fijo en CLP. La fecha de término debe ser posterior a la fecha de inicio.</p>

<h2>Uso en checkout</h2>
<p>Para aplicarse, un código debe existir, estar activo y encontrarse dentro de su vigencia. Los socios pueden validarlo desde <a href="#pricing">Planes y Membresías</a> o el <a href="#cart">Carrito de compras</a>.</p>

<h2>Limitaciones</h2>
<p>PulseFit Admin no permite eliminar códigos, establecer un límite de usos ni restringirlos a un plan específico.</p>
""".strip(),
            },
        ),
    },
)


def add_admin_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")

    for section_data in SECTIONS:
        section, _ = DocSection.objects.update_or_create(
            slug=section_data["slug"],
            defaults={
                "audience": "admin",
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


def remove_admin_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocSection.objects.filter(slug__in=[section["slug"] for section in SECTIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0004_add_member_guides"),
    ]

    operations = [
        migrations.RunPython(add_admin_guides, remove_admin_guides),
    ]
