"""Message composer variables and rendering (CYC-392 sibling: CYC-394).

Templates use ``{{ variable }}`` placeholders (whitespace tolerant). The
supported set is deliberately small and explicit; unknown variables fail
validation instead of rendering silently wrong.
"""

import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()

VARIABLE_PATTERN = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


class ComposerError(ValueError):
    """Raised when a template references unknown variables."""


def _display_name(user):
    return user.get_full_name() or user.username


def _remaining_credits(user):
    wallet = getattr(user, "wallet", None)
    return str(wallet.class_credits if wallet else 0)


VARIABLES = {
    "name": {
        "label": "Full name",
        "description": "Recipient's full name (username as fallback).",
        "sample": "Alex Rider",
        "resolve": _display_name,
    },
    "first_name": {
        "label": "First name",
        "description": "Recipient's first name.",
        "sample": "Alex",
        "resolve": lambda user: user.first_name or user.username,
    },
    "remaining_credits": {
        "label": "Remaining credits",
        "description": "Class credits left in the recipient's wallet.",
        "sample": "5",
        "resolve": _remaining_credits,
    },
}


def find_unknown_variables(*texts):
    referenced = set()
    for text in texts:
        referenced.update(VARIABLE_PATTERN.findall(text or ""))
    return sorted(referenced - set(VARIABLES))


def render_template(text, user=None):
    """Render ``text`` replacing variables with the recipient's values.

    Without a user, sample values are rendered so the composer preview
    always shows something meaningful.
    """
    if not text:
        return ""

    def replace(match):
        key = match.group(1)
        spec = VARIABLES.get(key)
        if spec is None:
            raise ComposerError(f"Unknown variable '{key}'.")
        if user is None:
            return spec["sample"]
        return str(spec["resolve"](user))

    return VARIABLE_PATTERN.sub(replace, text)


def get_sample_user(user_id):
    try:
        return User.objects.get(id=user_id, is_removed=False)
    except (User.DoesNotExist, ValidationError, ValueError, TypeError):
        return None
