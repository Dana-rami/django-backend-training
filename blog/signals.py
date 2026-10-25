import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Post

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Post)
def log_post_created(sender, instance, created, **kwargs):
    if created:
        logger.info(
            "A new post was created: id=%s title=%s",
            instance.id,
            instance.title,
        )
