from django.core.cache import cache
from django.db import connection, transaction

from .models import Author, AuthorProfile, Post

PUBLISHED_POST_COUNT_KEY = "blog:published-post-count"
PUBLISHED_POST_COUNT_TIMEOUT = 60


def create_post(*, title, content, is_published=False):
    return Post.objects.create(
        title=title,
        content=content,
        is_published=is_published,
    )


def published_post_count():
    """Return the number of published posts with one ORM count query."""
    return Post.objects.published().count()


def cached_published_post_count():
    """Return the published post count, shared by every caller.

    A cache miss stores the ORM count for 60 seconds under
    ``blog:published-post-count``. The value is not user-specific.
    Post changes can leave it stale until that timeout. This does not
    cache the post list, and ``published_post_count()`` stays uncached.
    """
    return cache.get_or_set(
        PUBLISHED_POST_COUNT_KEY,
        published_post_count,
        timeout=PUBLISHED_POST_COUNT_TIMEOUT,
    )


def published_post_count_raw():
    """Return the number of published posts with a parameterized query.

    Table and column names come from the Post model. The published flag is
    passed as a bound parameter and is not inserted into the SQL text.
    """
    table_name = connection.ops.quote_name(Post._meta.db_table)
    column_name = connection.ops.quote_name(
        Post._meta.get_field("is_published").column
    )
    sql = f"SELECT COUNT(*) FROM {table_name} WHERE {column_name} = %s"
    with connection.cursor() as cursor:
        cursor.execute(sql, [True])
        row = cursor.fetchone()
    return row[0]


def create_author_with_profile(*, name, email, bio):
    """Create an author and profile together.

    If the profile insert fails, the author insert is rolled back.
    """
    with transaction.atomic():
        author = Author.objects.create(name=name, email=email)
        AuthorProfile.objects.create(author=author, bio=bio)
    return author


def publish_post(post_id):
    """Publish one post inside a transaction.

    select_for_update() asks backends that support row locks to lock the
    selected row. Django's SQLite backend does not emit FOR UPDATE, so this
    function does not take a row lock on SQLite. The transaction still keeps
    the read and the update together.
    """
    with transaction.atomic():
        post = Post.objects.select_for_update().get(pk=post_id)
        post.is_published = True
        post.save(update_fields=["is_published"])
    return post


def bulk_create_posts(rows):
    """Insert many posts in one operation.

    bulk_create() does not call Model.save() and does not send pre_save or
    post_save. The post-create signal does not run for these rows.
    """
    posts = [
        Post(
            title=row["title"],
            content=row["content"],
            is_published=row.get("is_published", False),
        )
        for row in rows
    ]
    return Post.objects.bulk_create(posts)


def bulk_set_published(post_ids, *, is_published):
    """Set is_published on the given posts.

    bulk_update() does not call Model.save() and does not send pre_save or
    post_save. Posts whose ids are not included are left unchanged.
    """
    posts = list(Post.objects.filter(pk__in=post_ids).order_by("pk"))
    for post in posts:
        post.is_published = is_published
    if posts:
        Post.objects.bulk_update(posts, ["is_published"])
    return posts
