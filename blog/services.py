from .models import Post


def create_post(*, title, content, is_published=False):
    return Post.objects.create(
        title=title,
        content=content,
        is_published=is_published,
    )
