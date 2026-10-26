from django.db import models

from .expressions import CharLength


class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["email"],
                name="blog_author_email_uniq",
            ),
        ]

    def __str__(self):
        return self.name


class AuthorProfile(models.Model):
    author = models.OneToOneField(
        Author,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.TextField()

    def __str__(self):
        return self.author.name


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="blog_category_name_uniq",
            ),
        ]

    def __str__(self):
        return self.name


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_published=True)


class PostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def unpublished(self):
        return self.filter(is_published=False)

    def with_title_length(self):
        return self.annotate(title_length=CharLength("title"))

    def with_author(self):
        return self.select_related("author")

    def with_categories(self):
        return self.prefetch_related("categories")


class Post(models.Model):
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=False)
    objects = PostQuerySet.as_manager()
    published = PublishedManager()
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    categories = models.ManyToManyField(
        Category,
        blank=True,
        related_name="posts",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=["is_published", "id"],
                name="blog_post_published_id_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(title__gt=""),
                name="blog_post_title_not_empty",
            ),
            models.CheckConstraint(
                condition=~models.Q(title=models.F("content")),
                name="blog_post_title_ne_content",
            ),
        ]

    def __str__(self):
        return self.title
