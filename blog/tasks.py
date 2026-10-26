import logging

from celery import shared_task

from .services import published_post_count

logger = logging.getLogger(__name__)


@shared_task
def log_published_post_count():
    """Log how many posts are published.

    This task only reads. It does not write to the database, and post
    creation does not dispatch it. Callers that want it to follow a saved
    post should schedule it with transaction.on_commit().
    """
    count = published_post_count()
    logger.info("Published post count: %s", count)
    return count
