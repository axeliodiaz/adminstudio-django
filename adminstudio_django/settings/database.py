"""Postgres (Supabase) vs SQLite database configuration."""

from __future__ import annotations

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

_POSTGRES_SCHEMES = ("postgres://", "postgresql://")


def sqlite_databases(name: str | Path) -> dict:
    return {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": name,
            "OPTIONS": {"timeout": 20},
        }
    }


def databases_from_url(database_url: str) -> dict:
    """Parse a Postgres URI (Supabase session pooler recommended)."""
    url = database_url.strip()
    if not url.lower().startswith(_POSTGRES_SCHEMES):
        raise ImproperlyConfigured(
            "DATABASE_URL must be a Postgres URI (postgres:// or postgresql://). "
            "For Supabase, use the session pooler on port 5432, e.g. "
            "postgresql://postgres.<project-ref>:<password>@"
            "aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require"
        )

    import dj_database_url

    ssl_require = "sslmode=disable" not in url.lower()
    config = dj_database_url.parse(
        url,
        conn_max_age=0,
        conn_health_checks=True,
        ssl_require=ssl_require,
    )
    # PgBouncer / Supabase poolers reject Django server-side cursors.
    config["DISABLE_SERVER_SIDE_CURSORS"] = True
    return {"default": config}


def production_databases() -> dict:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ImproperlyConfigured(
            "Production requires DATABASE_URL pointing at Postgres. "
            "Set it on Render to the Supabase session pooler URI."
        )
    return databases_from_url(url)
