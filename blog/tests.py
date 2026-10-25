from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Post


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
