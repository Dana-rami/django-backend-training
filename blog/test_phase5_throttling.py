import os
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase
from rest_framework.throttling import SimpleRateThrottle

from config.environment import (
    DEFAULT_ANON_THROTTLE_RATE,
    DEFAULT_USER_THROTTLE_RATE,
    parse_throttle_rate,
)

THROTTLE_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "blog-phase5-throttle-tests",
    }
}
LOW_RATES = {"anon": "1/minute", "user": "1/minute"}


class ThrottleConfigurationTests(SimpleTestCase):
    def test_blank_values_use_the_defaults(self):
        for value in (None, "", "   "):
            self.assertEqual(
                parse_throttle_rate(value, DEFAULT_ANON_THROTTLE_RATE),
                "60/minute",
            )
            self.assertEqual(
                parse_throttle_rate(value, DEFAULT_USER_THROTTLE_RATE),
                "240/minute",
            )

    def test_rate_is_stripped_and_invalid_rates_are_rejected(self):
        self.assertEqual(parse_throttle_rate(" 120/hour ", "60/minute"), "120/hour")
        for value in ("fast", "0/minute", "10/month", "10/minute/extra"):
            with self.assertRaises(ValueError):
                parse_throttle_rate(value, "60/minute")

    def test_loaded_rates_follow_the_environment(self):
        anon = parse_throttle_rate(
            os.environ.get("ANON_THROTTLE_RATE"),
            DEFAULT_ANON_THROTTLE_RATE,
        )
        user = parse_throttle_rate(
            os.environ.get("USER_THROTTLE_RATE"),
            DEFAULT_USER_THROTTLE_RATE,
        )

        self.assertEqual(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["anon"], anon)
        self.assertEqual(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["user"], user)
        self.assertIn(
            "rest_framework.throttling.AnonRateThrottle",
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"],
        )
        self.assertIn(
            "rest_framework.throttling.UserRateThrottle",
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"],
        )


@override_settings(CACHES=THROTTLE_CACHE)
class ApiThrottleTests(APITestCase):
    def setUp(self):
        super().setUp()
        cache.clear()
        rate_patch = patch.object(SimpleRateThrottle, "THROTTLE_RATES", LOW_RATES)
        rate_patch.start()
        self.addCleanup(rate_patch.stop)

    def test_anonymous_requests_are_throttled(self):
        first = self.client.get("/blog/api/posts/")
        second = self.client.get("/blog/api/posts/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)

    def test_authenticated_requests_are_throttled_separately(self):
        user = get_user_model().objects.create_user(
            username="reader",
            password="test-password",
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        first = self.client.get("/blog/api/posts/")
        second = self.client.get("/blog/api/posts/")
        self.client.credentials()
        anonymous = self.client.get("/blog/api/posts/")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(anonymous.status_code, 200)

    def test_status_endpoint_is_not_throttled(self):
        self.client.get("/blog/api/posts/")
        blocked = self.client.get("/blog/api/posts/")
        status = self.client.get("/blog/api/status/")

        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json(), {"status": "ok"})
