from django.db import migrations


SECTIONS = (
    {
        "slug": "informacion-publica",
        "title": "Información pública",
        "order": 2,
        "pages": (
            {
                "slug": "como-explorar-instructores",
                "title": "Cómo explorar instructores y sus horarios",
                "summary": "Conoce al equipo, abre perfiles y revisa sus horarios.",
                "route": "#instructors",
                "order": 1,
                "body": """
<h2>Conoce al equipo</h2>
<p>Entra a <a href="#instructors">Instructores</a> desde el menú o el pie de página para ver los perfiles disponibles.</p>

<h2>Abre un perfil</h2>
<p>Selecciona una tarjeta para ver la foto, biografía y enlaces sociales del instructor. Cuando estén configuradas, también encontrarás playlists de Spotify, Apple Music o YouTube.</p>

<h2>Revisa sus horarios</h2>
<p>En el perfil puedes alternar entre vista de lista y calendario. Usa las flechas o el selector de fecha para cambiar de semana y revisar la hora, duración, sala y estudio de cada clase.</p>

<h2>Reserva una clase</h2>
<p>Para elegir un spot y confirmar tu asistencia, abre la clase desde <a href="#classes">Clases</a> y sigue la guía de reservas.</p>
""".strip(),
            },
            {
                "slug": "preguntas-frecuentes-publicas",
                "title": "Preguntas frecuentes públicas",
                "summary": "Consulta respuestas agrupadas por tema en un acordeón.",
                "route": "#faq",
                "order": 2,
                "body": """
<h2>Dónde encontrarlas</h2>
<p>Abre <a href="#faq">Preguntas frecuentes</a> desde el pie de página, en las secciones Soporte o Mi cuenta.</p>

<h2>Cómo leerlas</h2>
<p>Las preguntas están agrupadas por tema. Selecciona una sección para expandirla y luego una pregunta para leer su respuesta.</p>

<h2>Contenido actualizado</h2>
<p>El equipo del estudio administra este contenido desde el backoffice. Solo se muestran secciones y preguntas publicadas.</p>

<h2>Guías paso a paso</h2>
<p>Para aprender a usar clases, reservas, billetera y otras funciones, revisa también <a href="#docs">Documentación</a>.</p>
""".strip(),
            },
            {
                "slug": "documentos-legales",
                "title": "Documentos legales",
                "summary": "Consulta términos, aviso de privacidad y sus fechas de vigencia.",
                "route": "#legal/terms-and-conditions",
                "order": 3,
                "body": """
<h2>Documentos disponibles</h2>
<p>Desde el pie de página puedes abrir los <a href="#legal/terms-and-conditions">Términos y condiciones</a> y el <a href="#legal/privacy-policy">Aviso de privacidad</a>.</p>

<h2>Información de vigencia</h2>
<p>Cada documento muestra su título oficial, fecha de vigencia y fecha de última actualización.</p>

<h2>Enlaces directos</h2>
<p>Puedes acceder a <code>#legal/terms-and-conditions</code> o <code>#legal/terms</code> para los términos, y a <code>#legal/privacy-policy</code> o <code>#legal/privacy</code> para privacidad.</p>

<h2>Al comprar un plan</h2>
<p>Antes de pagar en el carrito debes aceptar los términos y condiciones. Puedes abrirlos desde el enlace mostrado allí.</p>
""".strip(),
            },
        ),
    },
    {
        "slug": "planes-y-compras",
        "title": "Planes y compras",
        "order": 3,
        "pages": (
            {
                "slug": "como-elegir-planes-y-membresias",
                "title": "Cómo elegir planes y membresías",
                "summary": "Compara membresías y paquetes, revisa beneficios y agrega un plan al carrito.",
                "route": "#pricing",
                "order": 1,
                "body": """
<h2>Dónde ver los planes</h2>
<p>Abre <a href="#pricing">Planes y Membresías</a> desde el menú principal. Puedes consultar precios y beneficios sin iniciar sesión.</p>

<h2>Membresías y paquetes</h2>
<p>Las membresías dan acceso por un periodo; los paquetes entregan créditos de clases. Cada tarjeta indica su precio, duración, clases incluidas cuando corresponda y beneficios activos.</p>

<h2>Agregar un plan</h2>
<p>Presiona <strong>Elegir plan</strong> o <strong>Comprar paquete</strong>. El producto se agrega al <a href="#cart">Carrito de compras</a>, donde podrás revisar la compra antes de pagar.</p>

<h2>Códigos promocionales</h2>
<p>En la pestaña <strong>Códigos promocionales</strong> puedes validar un descuento antes de pagar. También puedes aplicarlo desde el carrito.</p>
""".strip(),
            },
            {
                "slug": "carrito-de-compras",
                "title": "Cómo usar el carrito de compras",
                "summary": "Revisa productos, cantidades y descuentos antes de pagar.",
                "route": "#cart",
                "order": 2,
                "body": """
<h2>Acceder al carrito</h2>
<p>Abre <a href="#cart">Carrito de compras</a> desde el menú de tu cuenta o llega allí después de elegir un plan en <a href="#pricing">Planes y Membresías</a>.</p>

<h2>Revisar el pedido</h2>
<p>Verás cada plan con su precio, cantidad y subtotal. Puedes cambiar la cantidad o quitar un producto con <strong>Borrar</strong>.</p>
<p>El carrito se guarda en este navegador, por lo que puede no conservarse si usas otro dispositivo.</p>

<h2>Antes de pagar</h2>
<p>Debes aceptar los <a href="#legal/terms-and-conditions">términos y condiciones</a>. Para completar el pago necesitas iniciar sesión.</p>
""".strip(),
            },
            {
                "slug": "checkout-y-codigos-promocionales",
                "title": "Checkout y códigos promocionales",
                "summary": "Valida descuentos, elige método de pago y confirma tu compra.",
                "route": "#cart",
                "order": 3,
                "body": """
<h2>Aplicar un código promocional</h2>
<p>Valida tu código en la pestaña <strong>Códigos promocionales</strong> de <a href="#pricing">Planes y Membresías</a> o en el carrito, en el campo de descuento.</p>
<p>El sistema comprueba que el código exista, esté activo y esté dentro de su periodo de validez. Los descuentos pueden ser porcentuales o un monto fijo.</p>

<h2>Confirmar la compra</h2>
<p>El checkout ocurre dentro de <a href="#cart">Carrito de compras</a>. Elige Mercado Pago o Webpay Plus, acepta los términos y presiona <strong>Pagar</strong>.</p>

<h2>Después de pagar</h2>
<p>Tras una compra activada, el carrito se vacía y podrás revisar tus créditos en <a href="#wallet">Billetera</a>. También recibirás un comprobante por correo.</p>
""".strip(),
            },
            {
                "slug": "tu-billetera",
                "title": "Tu billetera: créditos, membresía e historial",
                "summary": "Consulta créditos, pases de invitado, beneficios y compras anteriores.",
                "route": "#wallet",
                "order": 4,
                "body": """
<h2>Abrir tu billetera</h2>
<p>Inicia sesión y entra a <a href="#wallet">Billetera</a> desde el menú de tu cuenta.</p>

<h2>Créditos y membresía</h2>
<p>Consulta tus créditos de clases, pases de invitado, plan activo, fecha de término y beneficios. Cada reserva consume un crédito, salvo que tengas una membresía ilimitada activa.</p>

<h2>Historial de compras</h2>
<p>La tabla muestra fecha, plan, monto pagado y periodo de vigencia de cada compra activada. Si todavía no tienes compras, verás un mensaje informativo.</p>

<h2>Después de comprar</h2>
<p>Los créditos y beneficios de una compra activada se reflejan aquí. Sin créditos ni membresía activa no podrás reservar clases; adquiere un plan en <a href="#pricing">Planes y Membresías</a>.</p>
""".strip(),
            },
        ),
    },
    {
        "slug": "mi-cuenta",
        "title": "Mi cuenta",
        "order": 4,
        "pages": (
            {
                "slug": "mi-perfil",
                "title": "Mi perfil",
                "summary": "Gestiona tu información personal, configuración de cycling y preferencias.",
                "route": "#profile",
                "order": 1,
                "body": """
<h2>Accede a tu perfil</h2>
<p>Inicia sesión y abre <a href="#profile">Mi perfil</a> desde el menú de usuario o el pie de página.</p>

<h2>Información personal</h2>
<p>Puedes editar tu nombre, apellido, género, fecha de nacimiento, dirección, altura y peso. Tu UUID se puede copiar, pero el nombre de usuario, correo electrónico y teléfono son solo lectura.</p>

<h2>Configuración cycling</h2>
<p>Guarda medidas de tu bici indoor: altura y distancia del asiento, distancia del manillar y talla de calzado de ciclismo.</p>

<h2>Preferencias de lista de espera</h2>
<p>Activa <strong>Auto-confirmar lista de espera</strong> para reservar automáticamente cuando se libere un spot. Si está desactivada, recibirás un correo y tendrás 15 minutos para confirmar.</p>

<h2>Guardar cambios</h2>
<p>Presiona <strong>Guardar cambios</strong> al final del formulario. Desde el perfil también puedes ir a <a href="#my-stats">Mis estadísticas</a>.</p>
""".strip(),
            },
            {
                "slug": "cuenta-y-autenticacion",
                "title": "Cuenta y autenticación",
                "summary": "Regístrate, confirma tu correo, inicia sesión y recupera tu contraseña.",
                "route": "#pricing",
                "order": 2,
                "body": """
<h2>Crear cuenta</h2>
<p>Pulsa <strong>Regístrate</strong> en la barra superior y completa nombre, apellido, correo, teléfono y contraseña. La contraseña debe tener al menos 8 caracteres.</p>
<p>Te enviaremos un correo de verificación. Hasta confirmarlo no podrás iniciar sesión.</p>

<h2>Confirmar tu correo e iniciar sesión</h2>
<p>Abre el enlace recibido por correo para activar tu cuenta. Luego usa <strong>Inicia sesión</strong> con tu correo o nombre de usuario y contraseña.</p>

<h2>Recuperar o cambiar contraseña</h2>
<p>En el inicio de sesión, elige <strong>¿Olvidaste tu contraseña?</strong>. Recibirás un código de 6 caracteres válido por 5 minutos si corresponde a una cuenta activa.</p>
<p>Si ya iniciaste sesión, ve a <a href="#profile">Mi perfil</a> y usa <strong>Cambiar contraseña</strong>; necesitarás tu contraseña actual.</p>

<h2>Correo y teléfono</h2>
<p>No puedes cambiar el correo ni teléfono desde el perfil. Si el estudio gestiona un cambio de correo, recibirás una solicitud de confirmación en la nueva dirección.</p>

<h2>Cerrar sesión</h2>
<p>En el menú de usuario, selecciona <strong>Cerrar sesión</strong>. Si tu sesión vence, deberás iniciar sesión nuevamente.</p>
""".strip(),
            },
            {
                "slug": "mis-reservas",
                "title": "Mis reservas",
                "summary": "Consulta tus clases agendadas por semana, en calendario o lista.",
                "route": "#my-reservations",
                "order": 3,
                "body": """
<h2>Accede a tus reservas</h2>
<p>Inicia sesión y abre <a href="#my-reservations">Mis reservas</a> desde el menú de usuario, el pie de página o el detalle de una clase después de confirmar tu spot.</p>

<h2>Calendario o lista</h2>
<p>Consulta tus clases en vista de <strong>Calendario</strong> o <strong>Lista</strong>. Usa las flechas o el selector de fecha para cambiar de semana.</p>

<h2>Detalles de cada reserva</h2>
<p>Cada entrada muestra hora, duración, estudio, sala y spot. En una reserva activa puedes abrir el detalle de la clase para cambiar de spot.</p>

<h2>Clases canceladas por el estudio</h2>
<p>Si el estudio cancela una clase, seguirá apareciendo marcada como <strong>Cancelada</strong> e indicará que el crédito fue devuelto. Las reservas que cancelaste dentro del plazo permitido no aparecen en esta lista.</p>

<h2>Sin reservas</h2>
<p>Si no tienes clases agendadas esa semana, podrás volver a <a href="#classes">Clases</a> para reservar.</p>
""".strip(),
            },
            {
                "slug": "lista-de-espera",
                "title": "Lista de espera",
                "summary": "Únete a una clase llena y confirma un cupo cuando se libere.",
                "route": "#waitlist",
                "order": 4,
                "body": """
<h2>Cuándo usarla</h2>
<p>Si una clase no tiene spots disponibles, puedes unirte desde su detalle en <a href="#classes">Clases</a>. Luego verás la entrada en <a href="#waitlist">Lista de espera</a>.</p>

<h2>Tu posición y estado</h2>
<p>En Lista de espera verás cada clase donde estás inscrito, tu posición en la fila y cuántos spots están ocupados.</p>

<h2>Si se libera un cupo</h2>
<p>El primer socio recibe un correo y tiene <strong>15 minutos</strong> para presionar <strong>Confirmar spot</strong>. Al confirmar, la reserva aparece en <a href="#my-reservations">Mis reservas</a>.</p>

<h2>Auto-confirmación</h2>
<p>En <a href="#profile">Mi perfil</a>, activa <strong>Auto-confirmar lista de espera</strong> para que el sistema reserve el spot automáticamente cuando se libere.</p>

<h2>Salir de la lista</h2>
<p>Puedes abandonar la lista en cualquier momento con <strong>Salir de la lista</strong>. Si tenías un cupo ofrecido, pasa al siguiente socio.</p>
""".strip(),
            },
            {
                "slug": "cancelaciones",
                "title": "Cancelaciones",
                "summary": "Conoce el plazo de cancelación gratuita y qué ocurre con tu crédito.",
                "route": "#classes",
                "order": 5,
                "body": """
<h2>Cancelar tu reserva</h2>
<p>Abre la clase desde <a href="#classes">Clases</a> y presiona <strong>Cancelar Reserva</strong>. Esta acción se realiza en el detalle de la clase, no desde Mis reservas.</p>

<h2>Ventana de cancelación gratuita</h2>
<p>Puedes cancelar sin perder crédito hasta N horas antes del inicio de la clase. El estudio configura este plazo y, por defecto, es de 2 horas.</p>

<h2>Después del plazo</h2>
<p>Una vez superado el límite, la app no permite cancelar la reserva y el crédito consumido no se devuelve.</p>

<h2>Cambiar de spot</h2>
<p>Desde el detalle de la misma clase puedes elegir otro spot disponible y confirmar el cambio sin cancelar tu reserva.</p>

<h2>Cancelación del estudio</h2>
<p>Si el estudio cancela la clase, recibirás un correo, verás la reserva cancelada en <a href="#my-reservations">Mis reservas</a> y se devolverá tu crédito.</p>
""".strip(),
            },
            {
                "slug": "mis-estadisticas",
                "title": "Mis estadísticas",
                "summary": "Revisa tu actividad, asistencia, créditos y preferencias de entrenamiento.",
                "route": "#my-stats",
                "order": 6,
                "body": """
<h2>Accede a tu dashboard</h2>
<p>Inicia sesión y abre <a href="#my-stats">Mis estadísticas</a> desde el menú de usuario, el pie de página o la tarjeta en <a href="#profile">Mi perfil</a>.</p>

<h2>Resumen de tu ritmo</h2>
<p>Verás horas totales en bici, clases completadas del año, racha semanal, porcentaje de asistencia, última visita, plan y estudio preferido cuando haya datos.</p>

<h2>Créditos y actividad</h2>
<p>La sección de billetera muestra clases usadas y créditos restantes. Con una membresía ilimitada verás uso sin límite de créditos.</p>

<h2>Gráficos y preferencias</h2>
<p>Explora tendencias mensuales, horarios, clases, coaches, días y spots favoritos, además de la asistencia frente a no-shows. Los gráficos se completan conforme asistes a clases.</p>

<h2>Coaches</h2>
<p>La sección <strong>Con quién sueles pedalear</strong> enlaza a los perfiles de los instructores con quienes más clases has tomado.</p>
""".strip(),
            },
        ),
    },
)


def add_member_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocPage = apps.get_model("docs", "DocPage")

    for section_data in SECTIONS:
        section, _ = DocSection.objects.update_or_create(
            slug=section_data["slug"],
            defaults={
                "audience": "member",
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


def remove_member_guides(apps, schema_editor):
    DocSection = apps.get_model("docs", "DocSection")
    DocSection.objects.filter(slug__in=[section["slug"] for section in SECTIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("docs", "0003_add_class_reservation_guide"),
    ]

    operations = [
        migrations.RunPython(add_member_guides, remove_member_guides),
    ]
