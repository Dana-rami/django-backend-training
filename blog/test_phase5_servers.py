from django.conf import settings
from django.test import SimpleTestCase, TestCase

import config.asgi
import config.wsgi


class AsyncStatusTests(TestCase):
    def test_status_returns_json_ok(self):
        response = self.client.get("/blog/api/status/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response["Content-Type"], "application/json")

    def test_status_does_not_query_the_database(self):
        with self.assertNumQueries(0):
            response = self.client.get("/blog/api/status/")

        self.assertEqual(response.status_code, 200)


class ApplicationLoadingTests(SimpleTestCase):
    def test_wsgi_and_asgi_applications_load(self):
        self.assertEqual(settings.WSGI_APPLICATION, "config.wsgi.application")
        self.assertEqual(settings.ASGI_APPLICATION, "config.asgi.application")
        self.assertTrue(callable(config.wsgi.application))
        self.assertTrue(callable(config.asgi.application))
