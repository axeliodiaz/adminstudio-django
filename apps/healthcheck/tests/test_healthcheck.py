from unittest.mock import patch

from django.db import connections
from django.db.utils import OperationalError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient


class HealthcheckTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("healthcheck")

    def test_healthcheck_ok(self):
        # When DB is accessible, it should return 200 and status ok
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("checks", data)
        self.assertEqual(data["checks"].get("app"), "ok")
        # In test DB should be available, expect database ok
        self.assertEqual(data["checks"].get("database"), "ok")

    def test_healthcheck_db_error_returns_503(self):
        # Mock the DB cursor to raise OperationalError
        with patch.object(
            connections["default"], "cursor", side_effect=OperationalError("db down")
        ):
            resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 503)
        data = resp.json()
        self.assertEqual(data.get("status"), "error")
        self.assertIn("checks", data)
        self.assertEqual(data["checks"].get("app"), "ok")
        # database check should contain error prefix
        self.assertTrue(str(data["checks"].get("database", "")).startswith("error:"))

    def test_anonymous_access_allowed(self):
        # APIClient without credentials should work
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
