import pytest
from django.core.exceptions import ImproperlyConfigured

from adminstudio_django.settings.database import databases_from_url, production_databases


def test_production_databases_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        production_databases()


def test_databases_from_url_rejects_sqlite(monkeypatch):
    with pytest.raises(ImproperlyConfigured, match="Postgres"):
        databases_from_url("sqlite:///tmp/db.sqlite3")


def test_databases_from_url_configures_supabase_pooler():
    url = (
        "postgresql://postgres.abc:secret@aws-0-us-west-1.pooler.supabase.com:5432/"
        "postgres?sslmode=require"
    )
    databases = databases_from_url(url)
    config = databases["default"]
    assert config["ENGINE"] == "django.db.backends.postgresql"
    assert config["DISABLE_SERVER_SIDE_CURSORS"] is True
    assert config["CONN_MAX_AGE"] == 0
    assert config["HOST"] == "aws-0-us-west-1.pooler.supabase.com"
    assert config["PORT"] == 5432
