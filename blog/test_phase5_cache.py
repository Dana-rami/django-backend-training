import os

import redis
from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from config.environment import cache_settings

from .models import Post
from .services import (
    PUBLISHED_POST_COUNT_KEY,
    PUBLISHED_POST_COUNT_TIMEOUT,
    cached_published_post_count,
)

LOC_MEM_CACHE = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "blog-phase5-tests",
    }
}


class CacheConfigurationTests(SimpleTestCase):
    def test_blank_redis_url_uses_local_memory(self):
        for value in (None, "", "   "):
            configured = cache_settings(value)
            self.assertEqual(
                configured["default"]["BACKEND"],
                "django.core.cache.backends.locmem.LocMemCache",
            )
            self.assertEqual(configured["default"]["LOCATION"], "blog-default")

    def test_redis_url_selects_the_redis_backend(self):
        configured = cache_settings(" redis://127.0.0.1:6379/1 ")

        self.assertEqual(
            configured["default"]["BACKEND"],
            "django.core.cache.backends.redis.RedisCache",
        )
        self.assertEqual(
            configured["default"]["LOCATION"],
            "redis://127.0.0.1:6379/1",
        )

    def test_loaded_cache_follows_redis_url(self):
        expected = cache_settings(os.environ.get("REDIS_URL"))

        self.assertEqual(
            settings.CACHES["default"]["BACKEND"],
            expected["default"]["BACKEND"],
        )
        self.assertTrue(
            settings.CACHES["default"]["LOCATION"]
            == expected["default"]["LOCATION"]
        )

    def test_redis_client_imports_without_connecting(self):
        self.assertTrue(callable(redis.ConnectionPool.from_url))


@override_settings(CACHES=LOC_MEM_CACHE)
class CachedPublishedPostCountTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_count_matches_published_posts(self):
        Post.objects.create(
            title="Published one",
            content="Body one",
            is_published=True,
        )
        Post.objects.create(
            title="Published two",
            content="Body two",
            is_published=True,
        )
        Post.objects.create(
            title="Draft title",
            content="Draft body",
            is_published=False,
        )

        self.assertEqual(cached_published_post_count(), 2)

    def test_zero_count_is_cached(self):
        with self.assertNumQueries(1):
            self.assertEqual(cached_published_post_count(), 0)
        with self.assertNumQueries(0):
            self.assertEqual(cached_published_post_count(), 0)

    def test_second_call_uses_the_cache(self):
        Post.objects.create(
            title="Published one",
            content="Body one",
            is_published=True,
        )

        with self.assertNumQueries(1):
            self.assertEqual(cached_published_post_count(), 1)

        self.assertEqual(cache.get(PUBLISHED_POST_COUNT_KEY), 1)
        with self.assertNumQueries(0):
            self.assertEqual(cached_published_post_count(), 1)

    def test_cached_count_stays_until_the_key_is_cleared(self):
        Post.objects.create(
            title="Published one",
            content="Body one",
            is_published=True,
        )
        self.assertEqual(cached_published_post_count(), 1)

        Post.objects.create(
            title="Published two",
            content="Body two",
            is_published=True,
        )
        self.assertEqual(cached_published_post_count(), 1)

        cache.delete(PUBLISHED_POST_COUNT_KEY)
        self.assertEqual(cached_published_post_count(), 2)
        self.assertEqual(PUBLISHED_POST_COUNT_TIMEOUT, 60)
