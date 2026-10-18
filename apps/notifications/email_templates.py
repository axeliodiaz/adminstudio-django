"""HTML email shells matching the PulseFit sketch (600px, inline styles)."""

from html import escape
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from apps.studios.branding import DEFAULT_BRANDING, FONT_CHOICES, HEX_COLOR_RE


def _readable_on(color):
    rgb = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in rgb]
    light = sum(v * w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    return "#FFFFFF" if 1.05 / (light + 0.05) >= (light + 0.05) / 0.05 else "#000000"


def _theme(branding=None):
    data = dict(DEFAULT_BRANDING)
    for key, value in (branding or {}).items():
        if key.endswith("_color") and (
            not isinstance(value, str) or not HEX_COLOR_RE.fullmatch(value)
        ):
            continue
        if key.endswith("_font") and value not in FONT_CHOICES:
            continue
        data[key] = value
    primary, bar = data["primary_color"], data["secondary_color"]
    return {
        "GOLD": primary,
        "NAVBAR": bar,
        "DARK": data["text_color"],
        "TEXT": data["text_color"],
        "MUTED": data["text_color"],
        "BG": data["background_color"],
        "SURFACE": data["background_color"],
        "BORDER": "#E0E0E0",
        "ON_GOLD": _readable_on(primary),
        "ON_DARK": _readable_on(bar),
        "FOOTER_TEXT": _readable_on(bar),
        "FONT": escape(data["body_font"]) + ", Arial, Helvetica, sans-serif",
        "HEADING_FONT": escape(data["heading_font"]) + ", Georgia, serif",
        "NAME": escape(data["name"]),
        "TAGLINE": escape(data["tagline"]),
        "data": data,
    }


def _studio_url(t, href):
    studio = t["data"].get("studio_id")
    if not studio:
        return href
    parts = urlsplit(href)
    query = dict(parse_qsl(parts.query))
    query["studio"] = str(studio)
    return urlunsplit(parts._replace(query=urlencode(query)))


def _cta_button(t, href: str, label: str) -> str:
    href = _studio_url(t, href)
    return f"""
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 24px">
  <tr>
    <td align="center" style="background-color:{t["GOLD"]};border-radius:6px">
      <a href="{escape(href, quote=True)}"
         style="display:inline-block;padding:12px 28px;font-family:{t["FONT"]};font-size:15px;font-weight:700;color:{t["ON_GOLD"]};text-decoration:none">
        {escape(label)}
      </a>
    </td>
  </tr>
</table>
"""


def _shell(t, *, preheader: str, body_html: str, frontend_url: str) -> str:
    logo = ""
    if t["data"].get("logo_svg"):
        query = urlencode({"studio": t["data"]["studio_id"]}) if t["data"].get("studio_id") else ""
        logo_url = frontend_url.rstrip("/") + "/api/brand-logo" + ("?" + query if query else "")
        logo = f'<img src="{escape(logo_url, quote=True)}" alt="{t["NAME"]}" width="120" style="display:block;max-width:120px;max-height:64px;margin-bottom:12px;object-fit:contain" />'
    legal = f"{frontend_url.rstrip('/')}/#legal/terms-and-conditions"
    privacy = f"{frontend_url.rstrip('/')}/#legal/privacy-policy"
    fonts = "&".join(
        "family=" + urlencode({"f": font})[2:] + ":wght@400;700"
        for font in {t["data"]["heading_font"], t["data"]["body_font"]}
    )
    legal, privacy = _studio_url(t, legal), _studio_url(t, privacy)
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="https://fonts.googleapis.com/css2?{escape(fonts, quote=True)}&amp;display=swap"></head>
<body style="margin:0;padding:0">
<span style="display:none;font-size:1px;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden">{escape(preheader)}</span>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;background-color:{t["BG"]};border-collapse:collapse">
  <tr>
    <td align="center" style="padding:32px 12px">
      <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="width:100%;max-width:600px;background-color:{t["SURFACE"]};border-collapse:collapse;border-radius:8px;overflow:hidden;border:1px solid {t["BORDER"]}">
        <tr>
          <td style="background-color:{t["NAVBAR"]};padding:22px 32px 18px;border-bottom:3px solid {t["GOLD"]};text-align:left">
            {logo}
            <span style="font-family:{t["HEADING_FONT"]};font-size:20px;font-weight:700;color:{t["ON_DARK"]}">{t["NAME"]}</span>
            <p style="margin:8px 0 0;font-family:{t["FONT"]};font-size:13px;color:{t["ON_DARK"]}">{t["TAGLINE"]}</p>
          </td>
        </tr>
        <tr>
          <td style="padding:32px 32px 8px;background-color:{t["SURFACE"]}">
            {body_html}
          </td>
        </tr>
        <tr>
          <td style="background-color:{t["NAVBAR"]};padding:28px 32px;text-align:center">
            <p style="margin:0 0 8px;font-family:{t["FONT"]};font-size:14px;font-weight:700;color:{t["ON_DARK"]}">{t["NAME"]}</p>
            <p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:12px;line-height:18px;color:{t["FOOTER_TEXT"]}">
              {t["TAGLINE"]}
            </p>
            <p style="margin:0;font-family:{t["FONT"]};font-size:11px;line-height:16px;color:{t["FOOTER_TEXT"]}">
              Recibes este correo porque tienes una cuenta en {t["NAME"]}.<br>
              <a href="{escape(legal, quote=True)}" style="color:{t["ON_DARK"]};text-decoration:underline">Términos</a>
              ·
              <a href="{escape(privacy, quote=True)}" style="color:{t["ON_DARK"]};text-decoration:underline">Privacidad</a>
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


def render_verify_email(
    *, email: str, verify_url: str, frontend_url: str, hours: int = 24, branding=None
) -> str:
    t = _theme(branding)
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Confirma tu correo</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Para terminar el registro de <strong>{escape(email)}</strong> confirma que este buzón es tuyo.
</p>
{_cta_button(t, verify_url, "Verificar correo")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  El enlace caduca en {hours} horas. Si no solicitaste una cuenta, ignora este mensaje.
</p>
"""
    return _shell(
        t,
        preheader="Un clic para activar tu cuenta. El enlace caduca en 24 horas.",
        body_html=body,
        frontend_url=frontend_url,
    )


def render_email_change(
    *, new_email: str, confirm_url: str, frontend_url: str, hours: int = 24, branding=None
) -> str:
    t = _theme(branding)
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Confirma tu nuevo correo</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Un administrador de {t["NAME"]} pidió cambiar el correo de tu cuenta a <strong>{escape(new_email)}</strong>.
  Confirma este buzón para completar el cambio.
</p>
{_cta_button(t, confirm_url, "Confirmar nuevo correo")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  El enlace caduca en {hours} horas. Si no esperabas este cambio, ignora este mensaje; tu correo actual no se modifica.
</p>
"""
    return _shell(
        t,
        preheader="Confirma tu nuevo correo. El enlace caduca en 24 horas.",
        body_html=body,
        frontend_url=frontend_url,
    )


def render_welcome_email(
    *, first_name: str, classes_url: str, frontend_url: str, branding=None
) -> str:
    t = _theme(branding)
    greeting = (
        f"Hola {escape(first_name)}, bienvenida al pelotón"
        if first_name
        else "Bienvenida al pelotón"
    )
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">{greeting}</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Tu cuenta en {t["NAME"]} ya está activa. Desde ahora puedes reservar clases de indoor cycling, elegir tu spot y gestionar tu plan desde la app o la web.
</p>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Te recomendamos completar tu perfil (tallas de bici y calzado) antes de la primera clase, así el coach puede dejarte lista en segundos.
</p>
{_cta_button(t, classes_url, "Reservar mi primera clase")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  Si no creaste esta cuenta, puedes ignorar este correo contactar a tu estudio.
</p>
"""
    return _shell(
        t,
        preheader="Tu cuenta ya está lista. Reserva tu primera clase.",
        body_html=body,
        frontend_url=frontend_url,
    )


def _detail_rows(t, rows: list[tuple[str, str]]) -> str:
    cells = []
    for label, value in rows:
        cells.append(f"""
<tr>
  <td style="padding:10px 0;border-bottom:1px solid {t["BORDER"]};font-family:{t["FONT"]};font-size:13px;color:{t["MUTED"]};width:38%;vertical-align:top">{escape(label)}</td>
  <td style="padding:10px 0;border-bottom:1px solid {t["BORDER"]};font-family:{t["FONT"]};font-size:15px;font-weight:700;color:{t["DARK"]};vertical-align:top">{escape(value)}</td>
</tr>
""")
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
    branding=None,
) -> str:
    t = _theme(branding)
    greeting_name = escape(first_name) if first_name else "rider"
    sala_spot = f"{room_name} · Spot {spot}"
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Tu spot está reservado</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  {greeting_name}, confirmamos tu reserva. Llega 10 minutos antes para montar la bici y dejar las pertenencias en lockers.
</p>
{_detail_rows(t, [
    ("Clase", class_title),
    ("Coach", coach_name),
    ("Cuando", when_label),
    ("Duración", f"{duration_minutes} min"),
    ("Estudio", studio_name),
    ("Sala / Spot", sala_spot),
])}
{_cta_button(t, reservation_url, "Ver mi reserva")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  Cancelación gratuita hasta {int(free_cancellation_hours)} horas antes. Después se descuenta el crédito.
</p>
"""
    preheader = f"Spot {spot} · {coach_name} · {room_name} · {studio_name}"
    return _shell(t, preheader=preheader, body_html=body, frontend_url=frontend_url)


def _notice_box(t, text: str, *, tone: str = "danger") -> str:
    if tone == "danger":
        bg, border, color = "#f8d7da", "#f1aeb5", "#58151c"
    elif tone == "success":
        bg, border, color = "#d1e7dd", "#a3cfbb", "#0a3622"
    else:
        bg, border, color = t["BG"], t["GOLD"], t["TEXT"]
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;margin:0 0 20px">
  <tr>
    <td style="padding:12px 14px;background-color:{bg};border-left:4px solid {border};font-family:{t["FONT"]};font-size:14px;line-height:20px;color:{color}">
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
    branding=None,
) -> str:
    t = _theme(branding)
    credit_line = (
        " El crédito ya está de vuelta en tu billetera."
        if credit_refunded
        else " Tu membresía ilimitada no descuenta créditos."
    )
    reason_text = (reason or "").strip() or "Cancelación del estudio"
    notice = f"Motivo: {reason_text}. No se descuenta asistencia."
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Tuvimos que cancelar la clase</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  La clase <strong>{escape(class_title)}</strong> del {escape(when_label)} con
  {escape(coach_name)} no se realizará.{credit_line}
</p>
{_notice_box(t, notice, tone="danger")}
{_cta_button(t, classes_url, "Ver otras clases del día")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  Si ya ibas en camino, la recepción del estudio puede orientarte con alternativas.
</p>
"""
    preheader = (
        "Devolvimos el crédito a tu billetera. Disculpa el cambio."
        if credit_refunded
        else "Disculpa el cambio. Puedes reservar otra clase."
    )
    return _shell(t, preheader=preheader, body_html=body, frontend_url=frontend_url)


def render_purchase_receipt(
    *,
    first_name: str,
    plan_name: str,
    amount_label: str,
    credits_label: str,
    validity_label: str,
    payment_method_label: str,
    folio: str,
    wallet_url: str,
    frontend_url: str,
    preheader: str,
    branding=None,
) -> str:
    t = _theme(branding)
    greeting_name = escape(first_name) if first_name else "rider"
    rows = [
        ("Plan", plan_name),
        ("Monto", amount_label),
        ("Créditos", credits_label),
        ("Vigencia", validity_label),
    ]
    if payment_method_label:
        rows.append(("Método", payment_method_label))
    rows.append(("Folio", folio))
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Pago recibido</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Gracias, {greeting_name}. Tu compra ya está activa en la billetera.
</p>
{_detail_rows(t, rows)}
{_cta_button(t, wallet_url, "Ver mi billetera")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  Este correo es tu comprobante. La boleta electrónica se envía por separado si aplica.
</p>
"""
    return _shell(t, preheader=preheader, body_html=body, frontend_url=frontend_url)


def render_gift_recipient(
    *,
    recipient_name: str,
    issuer_name: str,
    plan_name: str,
    message: str,
    redeem_url: str,
    expires_label: str,
    frontend_url: str,
    branding=None,
) -> str:
    t = _theme(branding)
    greeting = f"Hola {escape(recipient_name)}" if recipient_name else "Tienes un regalo"
    personal_message = (
        f'<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">'
        f"“{escape(message)}”</p>"
        if message
        else ""
    )
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">{greeting}</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  {escape(issuer_name or "Alguien")} te regaló <strong>{escape(plan_name)}</strong> para disfrutar en {t["NAME"]}.
</p>
{personal_message}
{_cta_button(t, redeem_url, "Canjear mi regalo")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  Inicia sesión o crea tu cuenta para canjearlo. El regalo vence el {escape(expires_label)}.
</p>
"""
    return _shell(
        t,
        preheader=f"Tienes un regalo: {plan_name}. Canjéalo antes del {expires_label}.",
        body_html=body,
        frontend_url=frontend_url,
    )


def _code_block(t, code: str) -> str:
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="width:100%;margin:8px 0 24px">
  <tr>
    <td align="center" style="padding:20px 16px;background-color:{t["BG"]};border:1px solid {t["BORDER"]};border-radius:8px">
      <span style="font-family:{t["FONT"]};font-size:32px;font-weight:700;letter-spacing:0.28em;color:{t["DARK"]}">
        {escape(code)}
      </span>
    </td>
  </tr>
</table>
"""


def render_password_recovery(
    *, reset_code: str, frontend_url: str, expiration_minutes: int = 5, branding=None
) -> str:
    t = _theme(branding)
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Recupera tu contraseña</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Usa este código en {t["NAME"]} para elegir una nueva contraseña. No lo compartas con nadie.
</p>
{_code_block(t, reset_code)}
{_notice_box(t, f"Caduca en {int(expiration_minutes)} minutos.", tone="info")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  Si no pediste recuperar tu cuenta, ignora este mensaje. Tu contraseña no cambia hasta que ingreses el código.
</p>
"""
    return _shell(
        t,
        preheader=f"Tu código es {reset_code}. Caduca en {int(expiration_minutes)} minutos.",
        body_html=body,
        frontend_url=frontend_url,
    )


def render_waitlist_offer(
    *,
    class_title: str,
    when_label: str,
    spot: int,
    action_url: str,
    frontend_url: str,
    auto_confirmed: bool = False,
    offer_minutes: int = 15,
    branding=None,
) -> str:
    t = _theme(branding)
    if auto_confirmed:
        body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Spot confirmado</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Se liberó un cupo en <strong>{escape(class_title)}</strong> ({escape(when_label)}).
  Como tienes auto-confirmación activa, reservamos el spot {int(spot)} por ti.
</p>
{_notice_box(t, f"Spot {int(spot)} reservado automáticamente.", tone="success")}
{_cta_button(t, action_url, "Ver mi reserva")}
"""
        preheader = f"Spot {int(spot)} confirmado en {class_title}."
    else:
        body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Se liberó un spot</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Hay un cupo disponible en <strong>{escape(class_title)}</strong> ({escape(when_label)}).
  Confirma el spot {int(spot)} desde Lista de espera antes de que expire la oferta.
</p>
{_notice_box(t, f"Tienes {int(offer_minutes)} minutos para confirmar.", tone="info")}
{_cta_button(t, action_url, "Ir a lista de espera")}
"""
        preheader = (
            f"Spot {int(spot)} libre en {class_title}. Confirma en {int(offer_minutes)} min."
        )
    return _shell(t, preheader=preheader, body_html=body, frontend_url=frontend_url)


def render_coach_substituted(
    *,
    class_title: str,
    when_label: str,
    studio_name: str,
    room_name: str,
    old_coach_name: str,
    new_coach_name: str,
    reason: str,
    action_url: str,
    frontend_url: str,
    audience: str = "reservation",
    branding=None,
) -> str:
    t = _theme(branding)
    if audience == "waitlist":
        cta_label = "Ver lista de espera"
        intro = (
            f"Sigue en lista de espera para <strong>{escape(class_title)}</strong>. "
            "Cambiamos al coach de la clase."
        )
    else:
        cta_label = "Ver mi reserva"
        intro = (
            f"Tu reserva en <strong>{escape(class_title)}</strong> se mantiene (mismo spot). "
            "Cambiamos al coach de la clase."
        )
    reason_text = (reason or "").strip()
    notice = f"Coach anterior: {old_coach_name}. Nuevo coach: {new_coach_name}." + (
        f" Motivo: {reason_text}." if reason_text else ""
    )
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Cambio de coach</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  {intro}
</p>
{_notice_box(t, notice, tone="info")}
{_detail_rows(t, [
    ("Clase", class_title),
    ("Cuando", when_label),
    ("Sede", studio_name),
    ("Sala", room_name),
    ("Coach anterior", old_coach_name),
    ("Nuevo coach", new_coach_name),
])}
{_cta_button(t, action_url, cta_label)}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["MUTED"]}">
  No tienes que hacer nada: tu lugar en la clase no cambia.
</p>
"""
    preheader = f"Nuevo coach: {new_coach_name} · {class_title}"
    return _shell(t, preheader=preheader, body_html=body, frontend_url=frontend_url)


def render_class_reminder(
    *,
    class_title: str,
    time_label: str,
    instructor_name: str,
    studio_name: str,
    room_name: str,
    spot: int | None,
    action_url: str,
    frontend_url: str,
    branding=None,
) -> str:
    t = _theme(branding)
    separator = " \u00b7 "
    location = separator.join(escape(bit) for bit in (studio_name, room_name) if bit)
    spot_label = f"{separator}Spot {int(spot)}" if spot else ""
    notice = _notice_box(
        t,
        "Lleva zapatillas de ciclismo (o avisa en recepci\u00f3n si necesitas pares de "
        "pr\u00e9stamo) y una toalla. Hidrataci\u00f3n en la sala.",
        tone="info",
    )
    cta = _cta_button(t, action_url, "Ver detalle de la clase")
    preheader = (
        f"Tu spot {int(spot)} te espera. Recuerda calzado de ciclismo y toalla."
        if spot
        else "Recuerda calzado de ciclismo y toalla."
    )
    heading = f"Nos vemos ma\u00f1ana a las {escape(time_label)}"
    cancel_note = (
        "\u00bfNo puedes ir? Cancela desde Mis reservas para liberar el spot "
        "a la lista de espera."
    )
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">{heading}</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Recordatorio de tu clase <strong>{escape(class_title)}</strong> con {escape(instructor_name)} en {location}{spot_label}.
</p>
{notice}
{cta}
<p style="margin:16px 0 0;font-family:{t["FONT"]};font-size:13px;line-height:20px;color:{t["TEXT"]}">
  {cancel_note}
</p>
"""
    return _shell(t, preheader=preheader, body_html=body, frontend_url=frontend_url)


def render_membership_expiry(
    *,
    plan_name: str,
    days_left: int,
    end_date_label: str,
    remaining_classes: int | None,
    total_classes: int | None,
    action_url: str,
    frontend_url: str,
    branding=None,
) -> str:
    t = _theme(branding)
    if days_left == 0:
        cadence = "vence hoy"
    elif days_left == 1:
        cadence = "caduca ma\u00f1ana"
    else:
        cadence = f"caduca en {days_left} d\u00edas"
    credits_line = ""
    if total_classes:
        credits_line = f" Te quedan {remaining_classes or 0} clases este ciclo."
    rows = [("Plan actual", plan_name), ("Vence", end_date_label)]
    if total_classes:
        rows.append(("Clases restantes", f"{remaining_classes or 0} de {total_classes}"))
    body = f"""
<h1 style="margin:0 0 12px;font-family:{t["HEADING_FONT"]};font-size:24px;font-weight:700;line-height:32px;color:{t["DARK"]}">Tu plan vence el {escape(end_date_label)}</h1>
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:15px;line-height:24px;color:{t["TEXT"]}">
  Tu plan <strong>{escape(plan_name)}</strong> {cadence}.{credits_line}
  Si renuevas ahora, los cr\u00e9ditos no usados no se arrastran: revisa condiciones en tu billetera.
</p>
{_detail_rows(t, rows)}
{_cta_button(t, action_url, "Renovar plan")}
<p style="margin:0 0 16px;font-family:{t["FONT"]};font-size:13px;line-height:20px;color:{t["MUTED"]}">
  Puedes cambiar a Unlimited o a un pack suelto desde Planes y Membres\u00edas.
</p>
"""
    return _shell(
        t,
        preheader="Renueva para no perder prioridad en lista de espera ni tus cr\u00e9ditos restantes.",
        body_html=body,
        frontend_url=frontend_url,
    )
