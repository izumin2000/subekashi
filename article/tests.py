"""
article アプリのビューテスト

ArticlesView・DefaultArticleView の HTTP レスポンスを検証する。
"""
from datetime import timedelta

from django.test import TestCase, Client, override_settings
from django.utils import timezone
from article.models import Article


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STATIC_STORAGE)
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

    def test_is_pinned_article_default_pins_howto_article_first(self):
        Article.objects.create(
            article_id="howToArticle",
            title="使い方記事",
            tag="howto",
            post_time=timezone.now() - timedelta(days=1),
            is_open=True,
        )
        response = self.client.get("/articles/")
        articles = list(response.context["articles"])
        self.assertEqual(articles[0].article_id, "howToArticle")

    def test_is_pinned_article_false_sorts_by_post_time_only(self):
        Article.objects.create(
            article_id="howToArticle",
            title="使い方記事",
            tag="howto",
            post_time=timezone.now() - timedelta(days=1),
            is_open=True,
        )
        self.client.cookies["is_pinned_article"] = "False"
        response = self.client.get("/articles/")
        articles = list(response.context["articles"])
        self.assertEqual(articles[0].article_id, self.article.article_id)


class ArticleModelTest(TestCase):
    """Article.get_top_news_articles() のテスト"""

    def test_news_tag_article_is_included(self):
        article = Article.objects.create(
            article_id="news-1", title="ニュース記事", tag="news",
            post_time=timezone.now(), is_open=True,
        )
        self.assertIn(article, Article.get_top_news_articles())

    def test_release_tag_article_is_included(self):
        article = Article.objects.create(
            article_id="release-1", title="リリース記事", tag="release",
            post_time=timezone.now(), is_open=True,
        )
        self.assertIn(article, Article.get_top_news_articles())

    def test_handle_as_news_article_is_included_regardless_of_tag(self):
        article = Article.objects.create(
            article_id="blog-as-news", title="ニュース扱いブログ", tag="blog",
            post_time=timezone.now(), is_open=True, handle_as_news=True,
        )
        self.assertIn(article, Article.get_top_news_articles())

    def test_other_tag_article_is_excluded(self):
        article = Article.objects.create(
            article_id="blog-1", title="通常ブログ", tag="blog",
            post_time=timezone.now(), is_open=True,
        )
        self.assertNotIn(article, Article.get_top_news_articles())

    def test_closed_article_is_excluded(self):
        article = Article.objects.create(
            article_id="news-closed", title="非公開ニュース", tag="news",
            post_time=timezone.now(), is_open=False,
        )
        self.assertNotIn(article, Article.get_top_news_articles())

    def test_future_post_time_article_is_excluded(self):
        article = Article.objects.create(
            article_id="news-future", title="未来投稿ニュース", tag="news",
            post_time=timezone.now() + timedelta(days=1), is_open=True,
        )
        self.assertNotIn(article, Article.get_top_news_articles())

    def test_limited_to_three_articles(self):
        for i in range(5):
            Article.objects.create(
                article_id=f"news-{i}", title=f"ニュース{i}", tag="news",
                post_time=timezone.now() - timedelta(days=i), is_open=True,
            )
        self.assertEqual(len(Article.get_top_news_articles()), 3)

    def test_ordered_by_post_time_desc(self):
        older = Article.objects.create(
            article_id="news-older", title="古いニュース", tag="news",
            post_time=timezone.now() - timedelta(days=2), is_open=True,
        )
        newer = Article.objects.create(
            article_id="news-newer", title="新しいニュース", tag="news",
            post_time=timezone.now() - timedelta(days=1), is_open=True,
        )
        result = list(Article.get_top_news_articles())
        self.assertLess(result.index(newer), result.index(older))


@override_settings(STORAGES=STATIC_STORAGE)
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
