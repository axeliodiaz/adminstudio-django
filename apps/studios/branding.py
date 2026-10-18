"""Studio branding rules: defaults, font allowlist, color validation, SVG sanitizer (CYC-428/429).

The logo is stored as sanitized SVG text in the database (no filesystem or
object storage, so it works on the free hosting tier). The sanitizer is an
allowlist: only known-safe elements and attributes survive, anything that can
run script or load external content is rejected or removed.
"""

import re
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
MAX_LOGO_BYTES = 100_000

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

# Curated free Google Fonts. A closed list keeps arbitrary strings out of the
# CSS / font URL the front builds from these values.
FONT_CHOICES = (
    "Rubik",
    "Inter",
    "Montserrat",
    "Poppins",
    "Lato",
    "Roboto",
    "Open Sans",
    "Nunito",
    "Work Sans",
    "DM Sans",
    "Bebas Neue",
    "Oswald",
    "Playfair Display",
    "Merriweather",
)

# Default base color is indigo, not the old PulseFit gold (#C9A66B).
DEFAULT_BRANDING = {
    "name": "PulseFit Studio",
    "tagline": "",
    "primary_color": "#4F46E5",
    "secondary_color": "#1F2937",
    "background_color": "#F8FAFC",
    "text_color": "#1F2937",
    "heading_font": "Rubik",
    "body_font": "Rubik",
    "logo_svg": "",
}

ALLOWED_TAGS = {
    "svg",
    "g",
    "path",
    "circle",
    "ellipse",
    "rect",
    "line",
    "polyline",
    "polygon",
    "defs",
    "lineargradient",
    "radialgradient",
    "stop",
    "clippath",
    "mask",
    "title",
    "desc",
    "text",
    "tspan",
    "symbol",
    "use",
}
# Elements that can run script, load remote content or animate attributes:
# the whole upload is refused instead of silently dropping them.
FORBIDDEN_TAGS = {
    "script",
    "foreignobject",
    "iframe",
    "embed",
    "object",
    "style",
    "image",
    "animate",
    "animatetransform",
    "animatemotion",
    "set",
    "a",
    "link",
    "audio",
    "video",
    "canvas",
    "feimage",
}
ALLOWED_ATTRS = {
    "viewbox",
    "width",
    "height",
    "x",
    "y",
    "x1",
    "x2",
    "y1",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "d",
    "points",
    "transform",
    "fill",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "stroke-miterlimit",
    "stroke-dasharray",
    "stroke-dashoffset",
    "stroke-opacity",
    "fill-opacity",
    "fill-rule",
    "clip-rule",
    "opacity",
    "id",
    "offset",
    "stop-color",
    "stop-opacity",
    "gradientunits",
    "gradienttransform",
    "fx",
    "fy",
    "clip-path",
    "mask",
    "preserveaspectratio",
    "font-family",
    "font-size",
    "font-weight",
    "text-anchor",
    "dx",
    "dy",
    "letter-spacing",
    "href",
    "style",
    "role",
    "aria-label",
    "version",
    "xmlns",
    "spreadmethod",
    "clippathunits",
    "maskunits",
    "maskcontentunits",
}
STYLE_PROPS = {
    "fill",
    "stroke",
    "stroke-width",
    "stroke-linecap",
    "stroke-linejoin",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "stop-color",
    "stop-opacity",
    "fill-rule",
    "clip-rule",
    "font-family",
    "font-size",
    "font-weight",
}
_URL_REF_RE = re.compile(r"url\(\s*(['\"]?)([^)]*)\1\s*\)", re.IGNORECASE)
_BAD_VALUE_RE = re.compile(r"javascript:|expression\(|@import|data:|\\|<|>", re.IGNORECASE)


class BrandingError(ValueError):
    """Raised when branding input fails validation."""


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def _safe_value(value: str) -> bool:
    if _BAD_VALUE_RE.search(value):
        return False
    for match in _URL_REF_RE.finditer(value):
        if not match.group(2).strip().startswith("#"):
            return False
    # url( without a closing form the regex understood
    return value.lower().count("url(") == len(_URL_REF_RE.findall(value))


def _clean_style(value: str) -> str:
    kept = []
    for declaration in value.split(";"):
        if ":" not in declaration:
            continue
        prop, _, val = declaration.partition(":")
        prop, val = prop.strip().lower(), val.strip()
        if prop in STYLE_PROPS and _safe_value(val):
            kept.append(f"{prop}:{val}")
    return ";".join(kept)


def _clean_element(element: ET.Element) -> None:
    for child in list(element):
        name = _local(child.tag)
        if name in FORBIDDEN_TAGS:
            raise BrandingError(f"El logo contiene un elemento no permitido: <{name}>.")
        if name not in ALLOWED_TAGS or not child.tag.startswith("{" + SVG_NS + "}"):
            element.remove(child)
            continue
        _clean_element(child)

    for key in list(element.attrib):
        value = element.attrib[key]
        local = _local(key)
        if key.startswith("{") and not key.startswith("{" + XLINK_NS + "}"):
            del element.attrib[key]
            continue
        if local.startswith("on") or local not in ALLOWED_ATTRS:
            del element.attrib[key]
            continue
        if local == "href":
            if not value.startswith("#"):
                del element.attrib[key]
            continue
        if local == "style":
            cleaned = _clean_style(value)
            if cleaned:
                element.attrib[key] = cleaned
            else:
                del element.attrib[key]
            continue
        if not _safe_value(value):
            del element.attrib[key]


def sanitize_svg(raw: str) -> str:
    """Return a sanitized copy of an SVG document or raise ``BrandingError``."""
    if not isinstance(raw, str):
        raise BrandingError("El logo debe ser texto SVG.")
    text = raw.strip()
    if not text:
        return ""
    if len(text.encode("utf-8")) > MAX_LOGO_BYTES:
        raise BrandingError("El logo supera el máximo de 100 KB.")
    lowered = text.lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise BrandingError("El logo no puede declarar DOCTYPE ni entidades.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        raise BrandingError("El archivo no es un SVG válido.") from None
    if root.tag != "{" + SVG_NS + "}svg":
        raise BrandingError("El archivo no es un SVG válido.")

    _clean_element(root)

    if not root.attrib.get("viewBox"):
        raise BrandingError("El SVG debe incluir un viewBox para escalar correctamente.")

    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    return ET.tostring(root, encoding="unicode")


def validate_hex_color(value: str, field: str) -> str:
    if not isinstance(value, str) or not HEX_COLOR_RE.match(value):
        raise BrandingError(f"{field}: usa un color hexadecimal como #4F46E5.")
    return value.upper()


def validate_font(value: str, field: str) -> str:
    if value not in FONT_CHOICES:
        raise BrandingError(f"{field}: tipografía no disponible.")
    return value
