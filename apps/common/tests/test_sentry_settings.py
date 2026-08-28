"""Sentry bootstrap helpers used to keep pytest noise out of Sentry."""

from adminstudio_django.settings.base import _is_running_tests


def test_is_running_tests_true_under_pytest():
    assert _is_running_tests() is True
