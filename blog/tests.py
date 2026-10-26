from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.db.models.signals import post_save
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Author, AuthorProfile, Category, Post
from .services import (
    bulk_create_posts,
    bulk_set_published,
    create_author_with_profile,
    create_post,
    publish_post,
    published_post_count,
    published_post_count_raw,
)


class PostApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="writer",
            password="test-password",
        )
        self.token = Token.objects.create(user=self.user)
        self.alpha = Post.objects.create(
            title="Alpha title",
            content="Unique alpha body",
            is_published=True,
        )
        self.beta = Post.objects.create(
            title="Beta title",
            content="Unique beta body",
            is_published=False,
        )
        self.gamma = Post.objects.create(
            title="Gamma title",
            content="Unique gamma body",
            is_published=True,
        )

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_get_post_list_without_authentication(self):
        response = self.client.get("/blog/api/posts/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("results", response.data)

    def test_get_single_post(self):
        response = self.client.get(f"/blog/api/posts/{self.alpha.id}/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Alpha title")
        self.assertEqual(response.data["content"], "Unique alpha body")

    def test_post_without_authentication_returns_401(self):
        response = self.client.post(
            "/blog/api/posts/",
            {"title": "New title", "content": "New content"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_post_with_valid_data_returns_201(self):
        self.authenticate()

        response = self.client.post(
            "/blog/api/posts/",
            {"title": "New title", "content": "New content"},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["title"], "New title")
        self.assertEqual(response.data["content"], "New content")
        self.assertIs(response.data["is_published"], False)
        self.assertIn("created_at", response.data)

    def test_post_can_set_is_published(self):
        self.authenticate()

        response = self.client.post(
            "/blog/api/posts/",
            {
                "title": "Published through API",
                "content": "Visible content",
                "is_published": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIs(response.data["is_published"], True)

    def test_put_without_authentication_returns_401(self):
        response = self.client.put(
            f"/blog/api/posts/{self.alpha.id}/",
            {"title": "Changed", "content": "Changed body"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_patch_without_authentication_returns_401(self):
        response = self.client.patch(
            f"/blog/api/posts/{self.alpha.id}/",
            {"title": "Changed"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_delete_without_authentication_returns_401(self):
        response = self.client.delete(f"/blog/api/posts/{self.alpha.id}/")

        self.assertEqual(response.status_code, 401)
        self.assertTrue(Post.objects.filter(id=self.alpha.id).exists())

    def test_invalid_token_is_rejected(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token invalid-token")

        response = self.client.post(
            "/blog/api/posts/",
            {"title": "New title", "content": "New content"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_post_rejects_spam_title(self):
        self.authenticate()

        response = self.client.post(
            "/blog/api/posts/",
            {"title": "This is spam", "content": "A real article"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_post_rejects_identical_title_and_content(self):
        self.authenticate()

        response = self.client.post(
            "/blog/api/posts/",
            {"title": "Same text", "content": "Same text"},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_patch_changes_only_supplied_field(self):
        self.authenticate()

        response = self.client.patch(
            f"/blog/api/posts/{self.beta.id}/",
            {"title": "Updated beta title"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Updated beta title")
        self.assertEqual(response.data["content"], "Unique beta body")

    def test_put_replaces_post(self):
        self.authenticate()

        response = self.client.put(
            f"/blog/api/posts/{self.beta.id}/",
            {"title": "Replaced title", "content": "Replaced content"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["title"], "Replaced title")
        self.assertEqual(response.data["content"], "Replaced content")

    def test_delete_returns_204(self):
        self.authenticate()

        response = self.client.delete(f"/blog/api/posts/{self.gamma.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.filter(id=self.gamma.id).exists())

    def test_pagination_returns_at_most_two_posts(self):
        page_one = self.client.get("/blog/api/posts/", {"page": 1})
        page_two = self.client.get("/blog/api/posts/", {"page": 2})

        self.assertEqual(page_one.status_code, 200)
        self.assertEqual(page_one.data["count"], 3)
        self.assertEqual(
            [post["title"] for post in page_one.data["results"]],
            ["Alpha title", "Beta title"],
        )
        self.assertIsNone(page_one.data["previous"])
        self.assertIsNotNone(page_one.data["next"])

        self.assertEqual(page_two.status_code, 200)
        self.assertEqual(page_two.data["count"], 3)
        self.assertEqual(
            [post["title"] for post in page_two.data["results"]],
            ["Gamma title"],
        )
        self.assertIsNotNone(page_two.data["previous"])
        self.assertIsNone(page_two.data["next"])

    def test_search_by_title_or_content(self):
        by_title = self.client.get("/blog/api/posts/", {"search": "Alpha"})
        by_content = self.client.get("/blog/api/posts/", {"search": "beta body"})

        self.assertEqual(by_title.status_code, 200)
        self.assertEqual(
            [post["title"] for post in by_title.data["results"]],
            ["Alpha title"],
        )
        self.assertEqual(by_content.status_code, 200)
        self.assertEqual(
            [post["title"] for post in by_content.data["results"]],
            ["Beta title"],
        )

    def test_search_with_no_matches_returns_empty_results(self):
        response = self.client.get("/blog/api/posts/", {"search": "zzzz-no-match"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_filter_is_published(self):
        published = self.client.get("/blog/api/posts/", {"is_published": "true"})
        unpublished = self.client.get("/blog/api/posts/", {"is_published": "false"})

        self.assertEqual(published.status_code, 200)
        self.assertEqual(
            {post["title"] for post in published.data["results"]},
            {"Alpha title", "Gamma title"},
        )
        self.assertEqual(unpublished.status_code, 200)
        self.assertEqual(
            [post["title"] for post in unpublished.data["results"]],
            ["Beta title"],
        )

    def test_filter_is_published_is_case_insensitive(self):
        published = self.client.get("/blog/api/posts/", {"is_published": "TRUE"})
        unpublished = self.client.get("/blog/api/posts/", {"is_published": "False"})

        self.assertEqual(published.status_code, 200)
        self.assertEqual(
            {post["title"] for post in published.data["results"]},
            {"Alpha title", "Gamma title"},
        )
        self.assertEqual(unpublished.status_code, 200)
        self.assertEqual(
            [post["title"] for post in unpublished.data["results"]],
            ["Beta title"],
        )

    def test_invalid_is_published_returns_400(self):
        response = self.client.get("/blog/api/posts/", {"is_published": "yes"})

        self.assertEqual(response.status_code, 400)
        self.assertIn("is_published", response.data)

    def test_patch_sets_is_published(self):
        self.authenticate()

        response = self.client.patch(
            f"/blog/api/posts/{self.beta.id}/",
            {"is_published": True},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIs(response.data["is_published"], True)
        self.beta.refresh_from_db()
        self.assertIs(self.beta.is_published, True)

    def test_filter_search_and_pagination_together(self):
        Post.objects.create(
            title="Alpha two",
            content="Second matching body",
            is_published=True,
        )
        Post.objects.create(
            title="Alpha three",
            content="Third matching body",
            is_published=True,
        )
        Post.objects.create(
            title="Alpha draft",
            content="Unpublished alpha body",
            is_published=False,
        )
        Post.objects.create(
            title="Published other",
            content="No shared keyword here",
            is_published=True,
        )

        response = self.client.get(
            "/blog/api/posts/",
            {"is_published": "true", "search": "Alpha", "page": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            [post["title"] for post in response.data["results"]],
            ["Alpha three"],
        )
        self.assertIsNotNone(response.data["previous"])
        self.assertIsNone(response.data["next"])


class Phase4OrmTests(TestCase):
    def test_post_has_published_id_index(self):
        indexes = {index.name: list(index.fields) for index in Post._meta.indexes}

        self.assertEqual(
            indexes["blog_post_published_id_idx"],
            ["is_published", "id"],
        )

    def test_blank_title_violates_check_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Post.objects.create(title="", content="A real body")

    def test_title_equal_to_content_violates_check_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Post.objects.create(title="Same text", content="Same text")

    def test_duplicate_author_email_violates_unique_constraint(self):
        Author.objects.create(name="First", email="same@example.com")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Author.objects.create(name="Second", email="same@example.com")

    def test_duplicate_category_name_violates_unique_constraint(self):
        Category.objects.create(name="News")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Category.objects.create(name="News")

    def test_valid_rows_satisfy_constraints(self):
        post = Post.objects.create(title="Valid title", content="Valid body")
        author = Author.objects.create(name="Ada", email="ada@example.com")
        profile = AuthorProfile.objects.create(author=author, bio="Writer")
        category = Category.objects.create(name="Notes")

        self.assertEqual(post.title, "Valid title")
        self.assertEqual(profile.bio, "Writer")
        self.assertEqual(category.name, "Notes")

    def test_with_title_length_matches_python_length(self):
        post = Post.objects.create(title="Alpha", content="Body text")

        annotated = Post.objects.with_title_length().get(pk=post.pk)

        self.assertEqual(annotated.title_length, len("Alpha"))

    def test_raw_published_count_matches_orm(self):
        Post.objects.create(title="Published one", content="Body one", is_published=True)
        Post.objects.create(title="Published two", content="Body two", is_published=True)
        Post.objects.create(title="Draft title", content="Draft body", is_published=False)

        self.assertEqual(published_post_count_raw(), 2)
        self.assertEqual(published_post_count(), 2)

    def test_published_post_count_uses_one_query(self):
        Post.objects.create(title="Published one", content="Body one", is_published=True)
        Post.objects.create(title="Draft title", content="Draft body", is_published=False)

        with self.assertNumQueries(1):
            self.assertEqual(published_post_count(), 1)

    def test_with_author_avoids_extra_queries(self):
        author = Author.objects.create(name="Ada", email="ada@example.com")
        for number in range(1, 4):
            Post.objects.create(
                title=f"Title {number}",
                content=f"Body {number}",
                author=author,
            )

        plain_posts = list(Post.objects.order_by("id"))
        with self.assertNumQueries(3):
            self.assertEqual(
                [post.author.name for post in plain_posts],
                ["Ada", "Ada", "Ada"],
            )

        loaded_posts = list(Post.objects.order_by("id").with_author())
        with self.assertNumQueries(0):
            self.assertEqual(
                [post.author.name for post in loaded_posts],
                ["Ada", "Ada", "Ada"],
            )

    def test_with_categories_avoids_extra_queries(self):
        news = Category.objects.create(name="News")
        notes = Category.objects.create(name="Notes")
        first = Post.objects.create(title="First title", content="First body")
        second = Post.objects.create(title="Second title", content="Second body")
        first.categories.add(news)
        second.categories.add(notes, news)

        plain_posts = list(Post.objects.order_by("id"))
        with self.assertNumQueries(2):
            self.assertEqual(
                [
                    sorted(category.name for category in post.categories.all())
                    for post in plain_posts
                ],
                [["News"], ["News", "Notes"]],
            )

        loaded_posts = list(Post.objects.order_by("id").with_categories())
        with self.assertNumQueries(0):
            self.assertEqual(
                [
                    sorted(category.name for category in post.categories.all())
                    for post in loaded_posts
                ],
                [["News"], ["News", "Notes"]],
            )

    def test_create_author_with_profile_saves_both(self):
        author = create_author_with_profile(
            name="Grace",
            email="grace@example.com",
            bio="Mathematician",
        )

        self.assertEqual(Author.objects.count(), 1)
        self.assertEqual(author.profile.bio, "Mathematician")

    def test_create_author_with_profile_rolls_back(self):
        with patch(
            "blog.services.AuthorProfile.objects.create",
            side_effect=RuntimeError("profile failed"),
        ):
            with self.assertRaises(RuntimeError):
                create_author_with_profile(
                    name="Grace",
                    email="grace@example.com",
                    bio="Mathematician",
                )

        self.assertFalse(Author.objects.filter(email="grace@example.com").exists())
        self.assertFalse(AuthorProfile.objects.exists())

    def test_publish_post_persists_flag(self):
        post = Post.objects.create(
            title="Draft title",
            content="Draft body",
            is_published=False,
        )

        publish_post(post.id)
        post.refresh_from_db()

        self.assertIs(post.is_published, True)

    def test_select_for_update_does_not_lock_rows_on_sqlite(self):
        post = Post.objects.create(title="Lock title", content="Lock body")

        with self.assertNumQueries(1) as captured:
            list(Post.objects.select_for_update().filter(pk=post.pk))

        sql = captured.captured_queries[0]["sql"]
        self.assertFalse(connection.features.has_select_for_update)
        self.assertNotIn("FOR UPDATE", sql.upper())

    def test_bulk_create_posts_inserts_rows_without_signals(self):
        created_titles = []

        def record_create(sender, instance, created, **kwargs):
            if created:
                created_titles.append(instance.title)

        post_save.connect(record_create, sender=Post)
        try:
            created = bulk_create_posts(
                [
                    {
                        "title": "Bulk one",
                        "content": "Body one",
                        "is_published": True,
                    },
                    {
                        "title": "Bulk two",
                        "content": "Body two",
                        "is_published": False,
                    },
                ]
            )
        finally:
            post_save.disconnect(record_create, sender=Post)

        self.assertEqual(created_titles, [])
        self.assertEqual(
            [post.title for post in created],
            ["Bulk one", "Bulk two"],
        )
        self.assertEqual(
            list(
                Post.objects.order_by("id").values_list("title", "is_published")
            ),
            [("Bulk one", True), ("Bulk two", False)],
        )

    def test_bulk_set_published_updates_only_selected_rows(self):
        keep = Post.objects.create(
            title="Keep title",
            content="Keep body",
            is_published=False,
        )
        change = Post.objects.create(
            title="Change title",
            content="Change body",
            is_published=False,
        )
        saved_ids = []

        def record_save(sender, instance, **kwargs):
            saved_ids.append(instance.pk)

        post_save.connect(record_save, sender=Post)
        try:
            bulk_set_published([change.id], is_published=True)
        finally:
            post_save.disconnect(record_save, sender=Post)

        keep.refresh_from_db()
        change.refresh_from_db()
        self.assertEqual(saved_ids, [])
        self.assertIs(keep.is_published, False)
        self.assertIs(change.is_published, True)

    def test_create_post_still_sends_signal(self):
        created_titles = []

        def record_create(sender, instance, created, **kwargs):
            if created:
                created_titles.append(instance.title)

        post_save.connect(record_create, sender=Post)
        try:
            create_post(title="Signal title", content="Signal body")
        finally:
            post_save.disconnect(record_create, sender=Post)

        self.assertEqual(created_titles, ["Signal title"])
