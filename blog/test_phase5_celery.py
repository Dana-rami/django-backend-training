import os
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase, TestCase

from config.celery import app as celery_app
from config.environment import celery_config

from .models import Post
from .services import create_post
from .tasks import log_published_post_count


class CeleryConfigurationTests(SimpleTestCase):
    def test_blank_broker_runs_tasks_in_process(self):
        for value in (None, "", "   "):
            configured = celery_config(value)

            self.assertEqual(configured["broker_url"], "memory://")
            self.assertIs(configured["task_always_eager"], True)
            self.assertIs(configured["task_eager_propagates"], True)

    def test_broker_url_waits_for_a_worker(self):
        configured = celery_config(" redis://127.0.0.1:6379/0 ")

        self.assertEqual(configured["broker_url"], "redis://127.0.0.1:6379/0")
        self.assertIs(configured["task_always_eager"], False)
        self.assertIs(configured["task_eager_propagates"], True)

    def test_loaded_settings_follow_the_environment(self):
        expected = celery_config(os.environ.get("CELERY_BROKER_URL"))

        self.assertTrue(settings.CELERY_BROKER_URL == expected["broker_url"])
        self.assertIs(
            settings.CELERY_TASK_ALWAYS_EAGER,
            expected["task_always_eager"],
        )
        self.assertIs(
            settings.CELERY_TASK_EAGER_PROPAGATES,
            expected["task_eager_propagates"],
        )

    def test_celery_app_loads(self):
        self.assertEqual(celery_app.main, "config")


class PublishedCountTaskTests(TestCase):
    def test_task_logs_the_count_without_writing(self):
        Post.objects.create(
            title="Published one",
            content="Body one",
            is_published=True,
        )
        Post.objects.create(
            title="Draft title",
            content="Draft body",
            is_published=False,
        )
        before = Post.objects.count()

        with self.assertLogs("blog.tasks", level="INFO") as captured:
            result = log_published_post_count.apply()

        self.assertEqual(result.result, 1)
        self.assertEqual(Post.objects.count(), before)
        self.assertIn("Published post count: 1", captured.output[0])

    def test_create_post_does_not_dispatch_the_task(self):
        with patch("blog.tasks.log_published_post_count.delay") as delay:
            create_post(title="Signal title", content="Signal body")

        delay.assert_not_called()
        self.assertEqual(Post.objects.count(), 1)
