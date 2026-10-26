import os
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.middleware.security import SecurityMiddleware
from django.test import RequestFactory, SimpleTestCase, override_settings

import config.settings as project_settings
from config.environment import (
    HSTS_ONE_YEAR,
    https_enabled,
    parse_allowed_hosts,
    security_settings,
)


class EnvironmentParsingTests(SimpleTestCase):
    def test_allowed_hosts_blank_values_return_an_empty_list(self):
        self.assertEqual(parse_allowed_hosts(None), [])
        self.assertEqual(parse_allowed_hosts(""), [])
        self.assertEqual(parse_allowed_hosts("   "), [])
        self.assertEqual(parse_allowed_hosts(","), [])

    def test_allowed_hosts_splits_and_strips_names(self):
        self.assertEqual(
            parse_allowed_hosts(" localhost , 127.0.0.1 "),
            ["localhost", "127.0.0.1"],
        )
        self.assertEqual(parse_allowed_hosts("example.com,"), ["example.com"])
        self.assertEqual(parse_allowed_hosts(".example.com"), [".example.com"])

    def test_allowed_hosts_rejects_a_wildcard(self):
        with self.assertRaises(ValueError):
            parse_allowed_hosts("*")
        with self.assertRaises(ValueError):
            parse_allowed_hosts("localhost, *")

    def test_loaded_allowed_hosts_come_from_the_environment(self):
        expected = parse_allowed_hosts(os.environ.get("ALLOWED_HOSTS"))
        actual = list(settings.ALLOWED_HOSTS)
        if actual[-1:] == ["testserver"] and "testserver" not in expected:
            actual = actual[:-1]

        self.assertEqual(actual, expected)
        self.assertNotIn("*", settings.ALLOWED_HOSTS)

    def test_https_flag_accepts_only_the_text_true(self):
        self.assertIs(https_enabled(None), False)
        self.assertIs(https_enabled("False"), False)
        self.assertIs(https_enabled("true"), False)
        self.assertIs(https_enabled("1"), False)
        self.assertIs(https_enabled("True"), True)

    def test_debug_parsing_is_unchanged(self):
        settings_text = Path(project_settings.__file__).read_text(encoding="utf-8")
        debug_rule = 'DEBUG = os.environ.get("DEBUG", "False") == "True"'

        self.assertIn(debug_rule, settings_text)
        self.assertIs(
            os.environ.get("MISSING_DEBUG_VALUE", "False") == "True",
            False,
        )

    def test_secret_key_is_required_from_the_environment(self):
        settings_text = Path(project_settings.__file__).read_text(encoding="utf-8")

        self.assertIn('SECRET_KEY = os.environ["SECRET_KEY"]', settings_text)
        self.assertTrue(settings.SECRET_KEY == os.environ["SECRET_KEY"])

    def test_use_https_false_keeps_transport_security_off(self):
        self.assertEqual(
            security_settings(False),
            {
                "SECURE_SSL_REDIRECT": False,
                "SESSION_COOKIE_SECURE": False,
                "CSRF_COOKIE_SECURE": False,
                "SECURE_HSTS_SECONDS": 0,
                "SECURE_HSTS_INCLUDE_SUBDOMAINS": False,
                "SECURE_HSTS_PRELOAD": False,
            },
        )

    def test_use_https_true_enables_transport_security(self):
        self.assertEqual(HSTS_ONE_YEAR, 31536000)
        self.assertEqual(
            security_settings(True),
            {
                "SECURE_SSL_REDIRECT": True,
                "SESSION_COOKIE_SECURE": True,
                "CSRF_COOKIE_SECURE": True,
                "SECURE_HSTS_SECONDS": 31536000,
                "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
                "SECURE_HSTS_PRELOAD": True,
            },
        )

    def test_loaded_security_settings_follow_use_https(self):
        expected = security_settings(https_enabled(os.environ.get("USE_HTTPS")))

        for name, value in expected.items():
            self.assertEqual(getattr(settings, name), value)


class SecurityHeaderTests(SimpleTestCase):
    def test_default_response_includes_baseline_headers(self):
        response = self.client.get("/blog/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["Referrer-Policy"], "same-origin")
        self.assertEqual(
            response.headers["Cross-Origin-Opener-Policy"],
            "same-origin",
        )
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")
        self.assertNotIn("Strict-Transport-Security", response.headers)
        self.assertNotIn("Content-Security-Policy", response.headers)

    @override_settings(**security_settings(False))
    def test_http_mode_does_not_redirect_or_send_hsts(self):
        middleware = SecurityMiddleware(lambda request: HttpResponse("ok"))

        plain = middleware(RequestFactory().get("/blog/"))
        secure = middleware(RequestFactory().get("/blog/", secure=True))

        self.assertEqual(plain.status_code, 200)
        self.assertNotIn("Strict-Transport-Security", plain.headers)
        self.assertEqual(secure.status_code, 200)
        self.assertNotIn("Strict-Transport-Security", secure.headers)
        self.assertIs(settings.SESSION_COOKIE_SECURE, False)
        self.assertIs(settings.CSRF_COOKIE_SECURE, False)

    @override_settings(**security_settings(True))
    def test_https_mode_redirects_plain_http_and_sends_hsts(self):
        middleware = SecurityMiddleware(lambda request: HttpResponse("ok"))

        plain = middleware(RequestFactory().get("/blog/"))
        secure = middleware(RequestFactory().get("/blog/", secure=True))

        self.assertEqual(plain.status_code, 301)
        self.assertTrue(plain["Location"].startswith("https://"))
        self.assertEqual(secure.status_code, 200)
        self.assertEqual(
            secure.headers["Strict-Transport-Security"],
            "max-age=31536000; includeSubDomains; preload",
        )
        self.assertIs(settings.SECURE_SSL_REDIRECT, True)
        self.assertIs(settings.SESSION_COOKIE_SECURE, True)
        self.assertIs(settings.CSRF_COOKIE_SECURE, True)
