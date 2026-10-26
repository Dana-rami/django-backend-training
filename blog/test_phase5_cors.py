import os

from django.conf import settings
from django.test import SimpleTestCase, override_settings

from config.environment import parse_cors_allowed_origins

LOCAL_ORIGIN = "http://localhost:3000"
OTHER_ORIGIN = "https://example.com"


class CorsParsingTests(SimpleTestCase):
    def test_blank_values_allow_no_origins(self):
        self.assertEqual(parse_cors_allowed_origins(None), [])
        self.assertEqual(parse_cors_allowed_origins(""), [])
        self.assertEqual(parse_cors_allowed_origins("   "), [])
        self.assertEqual(parse_cors_allowed_origins(","), [])

    def test_origins_are_split_and_stripped(self):
        self.assertEqual(
            parse_cors_allowed_origins(
                " http://localhost:3000 , https://example.com "
            ),
            [LOCAL_ORIGIN, OTHER_ORIGIN],
        )

    def test_wildcard_and_incomplete_origins_are_rejected(self):
        with self.assertRaises(ValueError):
            parse_cors_allowed_origins("*")
        with self.assertRaises(ValueError):
            parse_cors_allowed_origins("http://localhost:3000, *")
        with self.assertRaises(ValueError):
            parse_cors_allowed_origins("example.com")
        with self.assertRaises(ValueError):
            parse_cors_allowed_origins("https://example.com/app")

    def test_loaded_settings_follow_the_environment(self):
        expected = parse_cors_allowed_origins(
            os.environ.get("CORS_ALLOWED_ORIGINS")
        )

        self.assertEqual(list(settings.CORS_ALLOWED_ORIGINS), expected)
        self.assertIs(settings.CORS_ALLOW_ALL_ORIGINS, False)
        self.assertIs(settings.CORS_ALLOW_CREDENTIALS, False)

    def test_cors_middleware_runs_before_common_middleware(self):
        middleware = list(settings.MIDDLEWARE)
        security = middleware.index(
            "django.middleware.security.SecurityMiddleware"
        )
        cors = middleware.index("corsheaders.middleware.CorsMiddleware")
        common = middleware.index("django.middleware.common.CommonMiddleware")

        self.assertLess(security, cors)
        self.assertLess(cors, common)


class CorsRequestTests(SimpleTestCase):
    @override_settings(
        CORS_ALLOWED_ORIGINS=[LOCAL_ORIGIN],
        CORS_ALLOW_ALL_ORIGINS=False,
        CORS_ALLOW_CREDENTIALS=False,
    )
    def test_allowed_origin_is_echoed(self):
        response = self.client.get(
            "/blog/api/status/",
            headers={"Origin": LOCAL_ORIGIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"],
            LOCAL_ORIGIN,
        )
        self.assertNotIn("Access-Control-Allow-Credentials", response.headers)

    @override_settings(CORS_ALLOWED_ORIGINS=[LOCAL_ORIGIN])
    def test_disallowed_origin_is_not_echoed(self):
        response = self.client.get(
            "/blog/api/status/",
            headers={"Origin": OTHER_ORIGIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)

    @override_settings(CORS_ALLOWED_ORIGINS=[])
    def test_empty_configuration_allows_no_origin(self):
        response = self.client.get(
            "/blog/api/status/",
            headers={"Origin": LOCAL_ORIGIN},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)
