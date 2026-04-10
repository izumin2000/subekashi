"""
article アプリのビューテスト

ArticlesView・DefaultArticleView の HTTP レスポンスを検証する。
"""
from django.test import TestCase, Client, override_settings
from django.utils import timezone
from article.models import Article


STATIC_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class ArticlesViewTest(TestCase):
    """ArticlesView (/articles/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.article = Article.objects.create(
            article_id="test-articles-001",
            title="テスト記事タイトル",
            author="テスト筆者",
            tag="news",
            text="テスト記事本文",
            post_time=timezone.now(),
            is_open=True,
        )

    def test_get_returns_200(self):
        response = self.client.get("/articles/")
        self.assertEqual(response.status_code, 200)

    def test_tag_filter_returns_200(self):
        response = self.client.get("/articles/", {"tag": "news"})
        self.assertEqual(response.status_code, 200)

    def test_keyword_filter_returns_matching_article(self):
        response = self.client.get("/articles/", {"keyword": "テスト記事タイトル"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "テスト記事タイトル")

    def test_keyword_no_match_returns_200(self):
        response = self.client.get("/articles/", {"keyword": "存在しないキーワードXYZ"})
        self.assertEqual(response.status_code, 200)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class DefaultArticleViewTest(TestCase):
    """DefaultArticleView (/articles/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.article = Article.objects.create(
            article_id="test-default-001",
            title="詳細テスト記事",
            author="テスト筆者",
            tag="news",
            text="# 見出し\n本文テキスト",
            post_time=timezone.now(),
            is_open=True,
            is_md=True,
        )
        self.closed_article = Article.objects.create(
            article_id="test-default-002",
            title="非公開テスト記事",
            author="テスト筆者",
            tag="blog",
            text="非公開記事本文",
            post_time=timezone.now(),
            is_open=False,
        )

    def test_existing_open_article_returns_200(self):
        response = self.client.get(f"/articles/{self.article.article_id}/")
        self.assertEqual(response.status_code, 200)

    def test_article_title_appears_in_response(self):
        response = self.client.get(f"/articles/{self.article.article_id}/")
        self.assertContains(response, "詳細テスト記事")

    def test_nonexistent_article_returns_404(self):
        response = self.client.get("/articles/nonexistent-id-xyz/")
        self.assertEqual(response.status_code, 404)

    def test_closed_article_returns_404(self):
        response = self.client.get(f"/articles/{self.closed_article.article_id}/")
        self.assertEqual(response.status_code, 404)
