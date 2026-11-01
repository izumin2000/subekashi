"""
data.json（開発用の初期データ、#1286）のテスト

loaddataで読み込めること、全てのモデル・曲のカテゴリ・フラグ・各モデルの種別のデータが揃っていること、
statsコマンドを再実行しても月次統計が変わらないこと、初期データで主要な画面が表示できることを検証する。
モデルや曲のカテゴリ・フラグを追加したときにdata.jsonへのサンプルの追加を忘れないよう、データが無いとテストが失敗する。
"""
import os

from django.apps import apps
from django.core.management import call_command
from django.db.models import Count
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from article.models import Article
from config.settings import BASE_DIR
from subekashi.constants.constants import SONG_CATEGORIES, SONG_FLAGS
from subekashi.lib.query_filters import filter_by_lack
from subekashi.models import (
    Ad, Ai, Author, AuthorAlias, Contact, Editor, History, Prush, Song, SongLink, SongTimeline, Stats,
)
from subekashi.models.stats import SONGRANGE_CHOICES

STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

DATA_JSON_PATH = os.path.join(BASE_DIR, "data.json")

# SONG_FLAGSに無いが、Songのフラグとして扱うフィールド
EXTRA_SONG_FLAG_NAMES = ["is_lock", "is_removed"]


class DataJsonTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        call_command("loaddata", DATA_JSON_PATH, verbosity=0)

    def assertExists(self, queryset, message):
        self.assertTrue(queryset.exists(), f"data.jsonに{message}のデータがありません。サンプルを追加してください")


class DataJsonCoverageTest(DataJsonTestCase):
    """data.jsonが、モデル・種別・フラグの全てのデータを含んでいること"""

    def test_全てのモデルのデータがある(self):
        for model in apps.get_models():
            if model._meta.app_label not in ("subekashi", "article"):
                continue
            self.assertExists(model._base_manager.all(), model._meta.label)

    def test_曲のカテゴリごとの曲がある(self):
        for category in SONG_CATEGORIES:
            self.assertExists(Song.objects.filter(category=category["value"]), f"カテゴリ「{category['label']}」の曲")

    def test_曲のフラグごとの曲がある(self):
        for flag in SONG_FLAGS:
            name = flag["name"]
            if name == "is_lack":
                queryset = Song.all_objects.filter(filter_by_lack())
            elif name == "is_xx":
                queryset = Song.all_objects.filter(is_subeana=False, is_questionable=False)
            else:
                queryset = Song.all_objects.filter(**{name: True})
            self.assertExists(queryset, f"フラグ「{flag['label']}」の曲")
        for name in EXTRA_SONG_FLAG_NAMES:
            self.assertExists(Song.all_objects.filter(**{name: True}), f"{name}の曲")

    def test_曲の関係ごとの曲がある(self):
        self.assertExists(Song.objects.filter(is_subeana=True), "すべあな模倣曲")
        self.assertExists(Song.objects.filter(authors__id=1), "すべあな（作者ID1）の曲")
        self.assertExists(Song.objects.filter(imitates__isnull=False), "模倣元のある曲")
        self.assertExists(Song.objects.filter(imitateds__isnull=False), "模倣されている曲")
        self.assertExists(Song.objects.filter(prush__isnull=False), "プレラのある曲")
        self.assertExists(Song.objects.filter(upload_time__isnull=True), "アップロード日時の無い曲")
        self.assertExists(Song.objects.filter(view__isnull=True), "再生数の無い曲")
        self.assertExists(Song.objects.filter(links__isnull=True), "URLの無い曲")
        self.assertExists(Song.objects.annotate(count=Count("authors")).filter(count__gt=1), "複数の作者の曲")
        self.assertExists(Song.objects.annotate(count=Count("links")).filter(count__gt=1), "複数のURLの曲")

    def test_作者の別名と作者ページのURLがある(self):
        for alias_type, label in AuthorAlias.CHOICES:
            self.assertExists(AuthorAlias.objects.filter(alias_type=alias_type), f"別名の種別「{label}」")
        self.assertExists(Author.objects.filter(links__isnull=False), "URLのある作者")

    def test_曲のURLの種類ごとのデータがある(self):
        self.assertExists(SongLink.objects.filter(is_removed=True, songs__isnull=True), "deleteコマンドで削除されたURL")
        self.assertExists(
            SongLink.objects.filter(allow_dup=True).annotate(count=Count("songs")).filter(count__gt=1),
            "複数の曲で共有しているURL",
        )

    def test_年表の行がある(self):
        self.assertExists(SongTimeline.objects.filter(is_lyrics_blank=True), "歌詞列が空の年表の行")
        self.assertExists(SongTimeline.objects.filter(is_lyrics_blank=False), "歌詞列が空ではない年表の行")
        self.assertExists(Prush.objects.filter(date__isnull=False), "日付のあるプレラ")

    def test_編集者と編集履歴の種別ごとのデータがある(self):
        self.assertExists(Editor.objects.filter(is_open=True, is_forced_open=False, is_banned=False), "公開の編集者")
        self.assertExists(Editor.objects.filter(is_open=False, is_forced_open=False), "非公開の編集者")
        self.assertExists(Editor.objects.filter(is_forced_open=True), "強制公開の編集者")
        self.assertExists(Editor.objects.filter(is_banned=True), "BANされた編集者")
        self.assertTrue(Editor.objects.filter(pk=1).exists(), "timelineコマンドの編集者（ID1）がありません")
        for history_type, label in History.CHOICES:
            self.assertExists(History.objects.filter(history_type=history_type, song__isnull=False), f"曲の編集履歴「{label}」")
        self.assertExists(History.objects.filter(author__isnull=False), "作者の編集履歴")

    def test_お問い合わせと宣伝の種別ごとのデータがある(self):
        self.assertExists(Contact.get_answered(), "回答済みのお問い合わせ")
        self.assertExists(Contact.objects.filter(answer__isnull=True), "未回答のお問い合わせ")
        for status, label in Ad.CHOICES:
            self.assertExists(Ad.objects.filter(status=status), f"宣伝の状態「{label}」")

    def test_記事の種別ごとのデータがある(self):
        for tag, label in Article.TAGS:
            self.assertExists(Article.objects.filter(tag=tag), f"記事のタグ「{label}」")
        self.assertExists(Article.objects.filter(is_open=False), "非公開の記事")
        self.assertExists(Article.objects.filter(post_time__gt=timezone.now()), "公開前の記事")
        self.assertExists(Article.objects.filter(handle_as_news=True), "ニュースとして扱う記事")
        self.assertExists(Article.get_top_news_articles(), "トップ画面に表示するニュース・リリースの記事")
        self.assertExists(Article.objects.filter(pk="howToArticle"), "固定表示する記事（howToArticle）")

    def test_AiとWordのデータがある(self):
        self.assertExists(Ai.get_top_scored(), "高評価のAi")
        self.assertExists(Ai.get_unscored_janome(), "未採点のAi")
        self.assertTrue(Ai.get_all_janome().exclude(score__in=(0, 5)).exists(), "data.jsonに途中の点数のAiがありません")

    def test_月次統計がsongrangeごとにある(self):
        for songrange, label in SONGRANGE_CHOICES:
            self.assertExists(Stats.objects.filter(songrange=songrange), f"月次統計「{label}」")

    def test_statsコマンドを再実行しても月次統計が変わらない(self):
        fields = ["total_authors", "total_imitated_authors", "total_imitateds", "total_like", "total_view", "song_count"]

        def snapshot():
            return {(s.year, s.month, s.songrange): tuple(getattr(s, f) for f in fields) for s in Stats.objects.all()}

        before = snapshot()
        call_command("stats", verbosity=0)
        after = snapshot()

        # 月が替わると、data.jsonより新しい月の統計が増える
        for key, values in before.items():
            self.assertEqual(
                after[key], values,
                f"{key}の月次統計がstatsコマンドの結果と違います。data.jsonの月次統計を更新してください",
            )


@override_settings(STORAGES=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class DataJsonPagesTest(DataJsonTestCase):
    """data.jsonを読み込んだ開発用DBで、主要な画面が表示できること"""

    def test_一覧や統計の画面が表示できる(self):
        for name in ("top", "songs", "stats", "contact", "ai", "ai_result", "ad", "setting", "histories"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(f"subekashi:{name}")).status_code, 200)

    def test_全ての曲のページが表示できる(self):
        for song in Song.objects.all():
            with self.subTest(song=song.id):
                self.assertEqual(self.client.get(reverse("subekashi:song", args=[song.id])).status_code, 200)
                self.assertEqual(self.client.get(reverse("subekashi:song_history", args=[song.id])).status_code, 200)

    def test_ユーザーが削除した曲のページは削除の理由つきで410になる(self):
        for song in Song.all_objects.filter(is_removed=True):
            with self.subTest(song=song.id):
                reason = History.get_for_song(song).first().changes[1]
                response = self.client.get(reverse("subekashi:song", args=[song.id]))
                self.assertContains(response, reason, status_code=410)

    def test_全ての作者と編集者のページが表示できる(self):
        for author in Author.objects.all():
            with self.subTest(author=author.id):
                self.assertEqual(self.client.get(reverse("subekashi:author", args=[author.id])).status_code, 200)
                self.assertEqual(self.client.get(reverse("subekashi:author_aliases", args=[author.id])).status_code, 200)
        for editor in Editor.objects.all():
            with self.subTest(editor=editor.id):
                self.assertEqual(self.client.get(reverse("subekashi:editor", args=[editor.id])).status_code, 200)

    def test_カテゴリとフラグとプレラで曲を検索できる(self):
        queries = ["category=arrange", "is_lack=True", "is_draft=True", "is_joke=only", "is_subeana=xx", "is_original=True", "is_inst=True"]
        queries += [f"prush={prush.id}" for prush in Prush.objects.all()]
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"{reverse('subekashi:songs')}?{query}").status_code, 200)

    def test_非公開ではない記事のページが表示できる(self):
        for article in Article.objects.all():
            with self.subTest(article=article.article_id):
                response = self.client.get(reverse("article:default_article", args=[article.article_id]))
                self.assertEqual(response.status_code, 200 if article.is_open else 404)

    def test_記事の一覧には公開中の記事だけ表示される(self):
        response = self.client.get(reverse("article:articles"))
        self.assertEqual(response.status_code, 200)
        for article in Article.objects.all():
            with self.subTest(article=article.article_id):
                is_visible = article.is_open and article.post_time <= timezone.now()
                if is_visible:
                    self.assertContains(response, article.title)
                else:
                    self.assertNotContains(response, article.title)

    def test_回答済みのお問い合わせだけ表示される(self):
        response = self.client.get(reverse("subekashi:contact"))
        for contact in Contact.get_answered():
            self.assertContains(response, contact.detail)
        for contact in Contact.objects.filter(answer__isnull=True):
            self.assertNotContains(response, contact.detail)
