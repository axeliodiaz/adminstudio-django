"""HTML email shells matching the PulseFit sketch (600px, inline styles)."""

from html import escape

GOLD = "#C9A66B"
NAVBAR = "#212529"
DARK = "#333333"
TEXT = "#212121"
MUTED = "#6c757d"
BG = "#F5F5F5"
SURFACE = "#ffffff"
BORDER = "#e0e0e0"
ON_GOLD = "#000000"
ON_DARK = "#ffffff"
FOOTER_TEXT = "#d1d1d1"
FONT = "Arial, Helvetica, sans-serif"


def _cta_button(href: str, label: str) -> str:
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 24px">
  <tr>
    <td align="center" style="background-color:{GOLD};border-radius:6px">
      <a href="{escape(href, quote=True)}"
         style="display:inline-block;padding:12px 28px;font-family:{FONT};font-size:15px;font-weight:700;color:{ON_GOLD};text-decoration:none">
        {escape(label)}
      </a>
    </td>
  </tr>
</table>
"""


def _shell(*, preheader: str, body_html: str, frontend_url: str) -> str:
    legal = f"{frontend_url.rstrip('/')}/#legal/terms-and-conditions"
    privacy = f"{frontend_url.rstrip('/')}/#legal/privacy-policy"
    return f"""<!DOCTYPE html>
<html lang="es">
<body style="margin:0;padding:0">
<span style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden">{escape(preheader)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background-color:{BG};border-collapse:collapse">
  <tr>
    <td align="center" style="padding:32px 12px">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background-color:{SURFACE};border-collapse:collapse;border-radius:8px;overflow:hidden;border:1px solid {BORDER}">
        <tr>
          <td style="background-color:{NAVBAR};padding:22px 32px 18px;border-bottom:3px solid {GOLD};text-align:left">
            <span style="font-family:{FONT};font-size:20px;font-weight:700;color:{ON_DARK};letter-spacing:0.02em">PulseFit</span>
            <span style="font-family:{FONT};font-size:20px;font-weight:400;color:{GOLD};letter-spacing:0.02em"> Studio</span>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 32px 8px;background-color:{SURFACE}">
            {body_html}
          </td>
        </tr>
        <tr>
          <td style="background-color:{DARK};padding:28px 32px;text-align:center">
            <p style="margin:0 0 8px;font-family:{FONT};font-size:14px;font-weight:700;color:{ON_DARK}">PulseFit Studio</p>
            <p style="margin:0 0 16px;font-family:{FONT};font-size:12px;line-height:18px;color:{FOOTER_TEXT}">
              Indoor cycling · Patio Andino, 4770, Las Condes, Chile<br>
              Vitacura 5250, Vitacura, Chile
            </p>
            <p style="margin:0;font-family:{FONT};font-size:11px;line-height:16px;color:#9a9a9a">
              Recibes este correo porque tienes una cuenta en PulseFit.<br>
              <a href="{escape(legal, quote=True)}" style="color:{GOLD};text-decoration:underline">Términos</a>
              ·
              <a href="{escape(privacy, quote=True)}" style="color:{GOLD};text-decoration:underline">Privacidad</a>
            </p>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
</body>
</html>
"""


def render_verify_email(*, email: str, verify_url: str, frontend_url: str, hours: int = 24) -> str:
    body = f"""
<h1 style="margin:0 0 12px;font-family:{FONT};font-size:24px;font-weight:700;line-height:32px;color:{DARK}">Confirma tu correo</h1>
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{TEXT}">
  Para terminar el registro de <strong>{escape(email)}</strong> confirma que este buzón es tuyo.
</p>
{_cta_button(verify_url, "Verificar correo")}
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{MUTED}">
  El enlace caduca en {hours} horas. Si no solicitaste una cuenta, ignora este mensaje.
</p>
"""
    return _shell(
        preheader="Un clic para activar tu cuenta. El enlace caduca en 24 horas.",
        body_html=body,
        frontend_url=frontend_url,
    )


def render_email_change(
    *,
    new_email: str,
    confirm_url: str,
    frontend_url: str,
    hours: int = 24,
) -> str:
    body = f"""
<h1 style="margin:0 0 12px;font-family:{FONT};font-size:24px;font-weight:700;line-height:32px;color:{DARK}">Confirma tu nuevo correo</h1>
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{TEXT}">
  Un administrador de PulseFit pidió cambiar el correo de tu cuenta a <strong>{escape(new_email)}</strong>.
  Confirma este buzón para completar el cambio.
</p>
{_cta_button(confirm_url, "Confirmar nuevo correo")}
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{MUTED}">
  El enlace caduca en {hours} horas. Si no esperabas este cambio, ignora este mensaje; tu correo actual no se modifica.
</p>
"""
    return _shell(
        preheader="Confirma tu nuevo correo. El enlace caduca en 24 horas.",
        body_html=body,
        frontend_url=frontend_url,
    )


def render_welcome_email(*, first_name: str, classes_url: str, frontend_url: str) -> str:
    greeting = (
        f"Hola {escape(first_name)}, bienvenida al pelotón"
        if first_name
        else "Bienvenida al pelotón"
    )
    body = f"""
<h1 style="margin:0 0 12px;font-family:{FONT};font-size:24px;font-weight:700;line-height:32px;color:{DARK}">{greeting}</h1>
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{TEXT}">
  Tu cuenta en PulseFit Studio ya está activa. Desde ahora puedes reservar clases de indoor cycling, elegir tu spot y gestionar tu plan desde la app o la web.
</p>
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{TEXT}">
  Te recomendamos completar tu perfil (tallas de bici y calzado) antes de la primera clase — así el coach puede dejarte lista en segundos.
</p>
{_cta_button(classes_url, "Reservar mi primera clase")}
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{MUTED}">
  Si no creaste esta cuenta, puedes ignorar este correo o escribirnos a hola@pulsefit.cl.
</p>
"""
    return _shell(
        preheader="Tu cuenta ya está lista. Reserva tu primera clase en Patio Andino.",
        body_html=body,
        frontend_url=frontend_url,
    )


def _detail_rows(rows: list[tuple[str, str]]) -> str:
    cells = []
    for label, value in rows:
        cells.append(
            f"""
<tr>
  <td style="padding:10px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:13px;color:{MUTED};width:38%;vertical-align:top">{escape(label)}</td>
  <td style="padding:10px 0;border-bottom:1px solid {BORDER};font-family:{FONT};font-size:15px;font-weight:700;color:{DARK};vertical-align:top">{escape(value)}</td>
</tr>
"""
        )
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
        f'style="width:100%;border-collapse:collapse;margin:8px 0 20px">{"".join(cells)}</table>'
    )


def render_booking_confirmed(
    *,
    first_name: str,
    class_title: str,
    coach_name: str,
    when_label: str,
    duration_minutes: int,
    studio_name: str,
    room_name: str,
    spot: int,
    reservation_url: str,
    frontend_url: str,
    free_cancellation_hours: int = 2,
) -> str:
    greeting_name = escape(first_name) if first_name else "rider"
    sala_spot = f"{room_name} · Spot {spot}"
    body = f"""
<h1 style="margin:0 0 12px;font-family:{FONT};font-size:24px;font-weight:700;line-height:32px;color:{DARK}">Tu spot está reservado</h1>
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{TEXT}">
  {greeting_name}, confirmamos tu reserva. Llega 10 minutos antes para montar la bici y dejar las pertenencias en lockers.
</p>
{_detail_rows([
    ("Clase", class_title),
    ("Coach", coach_name),
    ("Cuando", when_label),
    ("Duración", f"{duration_minutes} min"),
    ("Estudio", studio_name),
    ("Sala / Spot", sala_spot),
])}
{_cta_button(reservation_url, "Ver mi reserva")}
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{MUTED}">
  Cancelación gratuita hasta {int(free_cancellation_hours)} horas antes. Después se descuenta el crédito.
</p>
"""
    preheader = f"Spot {spot} · {coach_name} · {room_name} · {studio_name}"
    return _shell(preheader=preheader, body_html=body, frontend_url=frontend_url)


def _notice_box(text: str, *, tone: str = "danger") -> str:
    if tone == "danger":
        bg, border, color = "#f8d7da", "#f1aeb5", "#58151c"
    elif tone == "success":
        bg, border, color = "#d1e7dd", "#a3cfbb", "#0a3622"
    else:
        bg, border, color = "#fff8e8", GOLD, DARK
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;margin:0 0 20px">
  <tr>
    <td style="padding:12px 14px;background-color:{bg};border-left:4px solid {border};font-family:{FONT};font-size:14px;line-height:20px;color:{color}">
      {escape(text)}
    </td>
  </tr>
</table>
"""


def render_class_cancelled(
    *,
    class_title: str,
    coach_name: str,
    when_label: str,
    reason: str,
    classes_url: str,
    frontend_url: str,
    credit_refunded: bool = True,
) -> str:
    credit_line = (
        " El crédito ya está de vuelta en tu billetera."
        if credit_refunded
        else " Tu membresía ilimitada no descuenta créditos."
    )
    reason_text = (reason or "").strip() or "Cancelación del estudio"
    notice = f"Motivo: {reason_text}. No se descuenta asistencia."
    body = f"""
<h1 style="margin:0 0 12px;font-family:{FONT};font-size:24px;font-weight:700;line-height:32px;color:{DARK}">Tuvimos que cancelar la clase</h1>
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{TEXT}">
  La clase <strong>{escape(class_title)}</strong> del {escape(when_label)} con
  {escape(coach_name)} no se realizará.{credit_line}
</p>
{_notice_box(notice, tone="danger")}
{_cta_button(classes_url, "Ver otras clases del día")}
<p style="margin:0 0 16px;font-family:{FONT};font-size:15px;line-height:24px;color:{MUTED}">
  Si ya ibas en camino, recepción en Patio Andino puede orientarte con alternativas.
</p>
"""
    preheader = (
        "Devolvimos el crédito a tu billetera. Disculpa el cambio."
        if credit_refunded
        else "Disculpa el cambio. Puedes reservar otra clase."
    )
    return _shell(preheader=preheader, body_html=body, frontend_url=frontend_url)
