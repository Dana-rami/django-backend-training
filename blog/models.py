from django.db import models


class Author(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

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

    def __str__(self):
        return self.title
