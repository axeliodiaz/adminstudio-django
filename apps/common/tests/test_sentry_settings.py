"""Sentry bootstrap helpers used to keep pytest noise out of Sentry."""

import os
import types

import adminstudio_django.settings.base as base


def test_is_running_tests_true_under_pytest():
    assert base._is_running_tests() is True


def test_is_running_tests_detects_pytest_env(monkeypatch):
    monkeypatch.setenv("PYTEST_VERSION", "8.3.0")
    fake_sys = types.SimpleNamespace(argv=["manage.py", "runserver"], modules={})
    monkeypatch.setattr(base, "sys", fake_sys)
    assert base._is_running_tests() is True


def test_is_running_tests_detects_pytest_argv(monkeypatch):
    monkeypatch.delenv("PYTEST_VERSION", raising=False)
    fake_sys = types.SimpleNamespace(argv=["/venv/bin/pytest", "-q"], modules={})
    monkeypatch.setattr(base, "sys", fake_sys)
    assert base._is_running_tests() is True


def test_is_running_tests_detects_pytest_module(monkeypatch):
    monkeypatch.delenv("PYTEST_VERSION", raising=False)
    fake_sys = types.SimpleNamespace(argv=["manage.py", "runserver"], modules={"pytest": object()})
    monkeypatch.setattr(base, "sys", fake_sys)
    assert base._is_running_tests() is True


def test_is_running_tests_false_outside_pytest(monkeypatch):
    monkeypatch.delenv("PYTEST_VERSION", raising=False)
    fake_sys = types.SimpleNamespace(argv=["gunicorn", "adminstudio_django.wsgi"], modules={})
    monkeypatch.setattr(base, "sys", fake_sys)
    assert base._is_running_tests() is False


def test_sentry_dsn_cleared_in_conftest():
    """Root conftest forces SENTRY_DSN empty so LoggingIntegration never fires in pytest."""
    assert os.environ.get("SENTRY_DSN", "") == ""
