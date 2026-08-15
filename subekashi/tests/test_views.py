"""
ビューの HTTP レスポンステスト

各ページの基本的なアクセス可否・ステータスコード・リダイレクト先を検証する。
ManifestStaticFilesStorage はテストに不要なため StaticFilesStorage に差し替える。
"""
from unittest.mock import patch
from django.db import connection
from django.test import TestCase, Client, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from subekashi.forms import AuthorAliasForm
from subekashi.models import Ad, Author, AuthorAlias, Contact, Editor, History, Song


STATIC_STORAGE = "django.contrib.staticfiles.storage.StaticFilesStorage"


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class TopViewTest(TestCase):
    """TopView (/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:top"))
        self.assertEqual(response.status_code, 200)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongsViewTest(TestCase):
    """SongsView (/songs/) のテスト"""

    def setUp(self):
        self.client = Client()
        Song.objects.create(title="検索テスト曲", lyrics="歌詞")

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:songs"))
        self.assertEqual(response.status_code, 200)

    def test_keyword_search_returns_200(self):
        response = self.client.get(reverse("subekashi:songs"), {"keyword": "テスト"})
        self.assertEqual(response.status_code, 200)

    def test_invalid_page_returns_200(self):
        response = self.client.get(reverse("subekashi:songs"), {"page": "abc"})
        self.assertEqual(response.status_code, 200)

    def test_pagination_params_return_200(self):
        response = self.client.get(reverse("subekashi:songs"), {"page": "1", "size": "10"})
        self.assertEqual(response.status_code, 200)

    def test_bool_query_param_true_uppercase_sets_context(self):
        """is_draft=True (大文字) でチェックボックスが有効になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "True"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_draft"])

    def test_bool_query_param_1_sets_context(self):
        """is_draft=1 でチェックボックスが有効になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "1"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_draft"])

    def test_bool_query_param_false_uppercase_sets_context(self):
        """is_draft=False (大文字) でチェックボックスが無効になること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_draft": "False"})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_draft"])

    def test_is_joke_true_sets_jokerange_only(self):
        """is_joke=True でjokerangeがonlyになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "True"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "only")

    def test_is_joke_only_sets_jokerange_only(self):
        """is_joke=only でjokerangeがonlyになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "only"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "only")

    def test_is_joke_false_sets_jokerange_off(self):
        """is_joke=False でjokerangeがoffになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "False"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "off")

    def test_is_joke_off_sets_jokerange_off(self):
        """is_joke=off でjokerangeがoffになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "off"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "off")

    def test_is_joke_all_sets_jokerange_on(self):
        """is_joke=all でjokerangeがonになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "all"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "on")

    def test_is_joke_on_sets_jokerange_on(self):
        """is_joke=on でjokerangeがonになること"""
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "on"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "on")

    def test_bool_query_params_all_fields(self):
        """is_original/is_inst/is_questionable でもTrue/Falseが正しく変換されること"""
        for field in ["is_original", "is_inst", "is_questionable"]:
            with self.subTest(field=field):
                response = self.client.get(reverse("subekashi:songs"), {field: "True"})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context[field])

    def test_is_subeana_query_param_does_not_overwrite_saved_songrange_cookie(self):
        """曲詳細ページのタグリンク(is_subeana)経由の絞り込みでsearch_songrange cookieが上書きされないこと"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_songrange"] = "subeana"
        response = self.client.get(reverse("subekashi:songs"), {"is_subeana": "xx"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["songrange"], "xx")
        self.assertNotIn("search_songrange", response.cookies)

    def test_is_joke_query_param_does_not_overwrite_saved_jokerange_cookie(self):
        """曲詳細ページのタグリンク(is_joke)経由の絞り込みでsearch_jokerange cookieが上書きされないこと"""
        self.client.cookies["is_saved_select"] = "on"
        self.client.cookies["search_jokerange"] = "on"
        response = self.client.get(reverse("subekashi:songs"), {"is_joke": "only"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["jokerange"], "only")
        self.assertNotIn("search_jokerange", response.cookies)

    def test_songrange_query_param_still_saves_cookie(self):
        """検索フォーム経由(songrange)の変更は引き続きcookieに保存されること"""
        self.client.cookies["is_saved_select"] = "on"
        response = self.client.get(reverse("subekashi:songs"), {"songrange": "xx"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.cookies["search_songrange"].value, "xx")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongViewTest(TestCase):
    """SongView (/songs/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="詳細テスト曲", lyrics="歌詞")

    def test_existing_song_returns_200(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_song_title_appears_in_response(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, "詳細テスト曲")

    def test_questionable_tag_appears_when_is_questionable(self):
        self.song.is_questionable = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, "界隈曲?")

    def test_questionable_tag_not_shown_by_default(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, "界隈曲?")

    def test_noindex_not_shown_by_default(self):
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertNotContains(response, 'name="robots"')

    def test_noindex_shown_when_is_questionable(self):
        self.song.is_questionable = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')

    def test_noindex_shown_when_is_limited(self):
        self.song.is_limited = True
        self.song.save()
        response = self.client.get(reverse("subekashi:song", args=[self.song.id]))
        self.assertContains(response, '<meta name="robots" content="noindex, nofollow">')


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongNewViewTest(TestCase):
    """SongNewView (/songs/new/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_new"))
        self.assertEqual(response.status_code, 200)

    def test_post_non_youtube_url_returns_error(self):
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "https://example.com/video", "authors": "テスト作者", "title": "テスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("YouTube", response.context["error"])

    def test_post_empty_authors_returns_error(self):
        # URL なし・作者空白 → 作者バリデーションエラー
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "  ", "title": "テスト曲"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("作者", response.context["error"])

    def test_post_empty_title_returns_error(self):
        # URL なし・作者あり・タイトル空白 → タイトルバリデーションエラー
        response = self.client.post(
            reverse("subekashi:song_new"),
            {"url": "", "authors": "テスト作者", "title": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("タイトル", response.context["error"])

    def test_post_questionable_forces_original_false(self):
        # is-questionable時、オリジナル模倣はユーザーの入力値に関わらず強制的にFalseになる
        response = self.client.post(
            reverse("subekashi:song_new"),
            {
                "url": "",
                "authors": "界隈曲テスト作者",
                "title": "界隈曲テスト曲",
                "is-questionable-manual": "on",
                "is-original-manual": "on",
                "is-subeana-manual": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        song = Song.objects.get(title="界隈曲テスト曲")
        self.assertTrue(song.is_questionable)
        self.assertFalse(song.is_original)
        self.assertTrue(song.is_subeana)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongEditViewTest(TestCase):
    """SongEditView (/songs/<id>/edit/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="編集テスト曲")

    def test_existing_song_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_edit", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_edit", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_post_questionable_forces_lyrics_and_imitate_blank(self):
        # is_questionable時、歌詞・模倣・下書きはユーザー入力に関わらず空/OFFになる
        imitate_target = Song.objects.create(title="模倣元テスト曲")
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "",
                "imitate": str(imitate_target.id),
                "lyrics": "本来は保存されないはずの歌詞",
                "is_questionable": True,
                "is_draft": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertTrue(self.song.is_questionable)
        self.assertEqual(self.song.lyrics, "")
        self.assertFalse(self.song.is_draft)
        self.assertNotIn(imitate_target, self.song.imitates.all())

    def test_post_questionable_honors_deleted_joke_inst_subeana_but_forces_original_false(self):
        # is_questionable時、非公開/削除済み・ネタ曲・インスト・すべあな界隈曲の入力値は保存されるが、
        # オリジナル模倣は入力値に関わらず強制的にFalseになる
        response = self.client.post(
            reverse("subekashi:song_edit", args=[self.song.id]),
            {
                "title": "編集テスト曲",
                "authors": "編集テスト作者",
                "url": "",
                "imitate": "",
                "lyrics": "",
                "is_questionable": True,
                "is_original": True,
                "is_deleted": True,
                "is_joke": True,
                "is_inst": True,
                "is_subeana": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.song.refresh_from_db()
        self.assertTrue(self.song.is_questionable)
        self.assertFalse(self.song.is_original)
        self.assertTrue(self.song.is_deleted)
        self.assertTrue(self.song.is_joke)
        self.assertTrue(self.song.is_inst)
        self.assertTrue(self.song.is_subeana)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongHistoryViewTest(TestCase):
    """SongHistoryView (/songs/<id>/history/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="履歴テスト曲")

    def test_existing_song_returns_200(self):
        response = self.client.get(reverse("subekashi:song_history", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_history", args=[99999]))
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class SongDeleteViewTest(TestCase):
    """SongDeleteView (/songs/<id>/delete/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.song = Song.objects.create(title="削除申請テスト曲")

    def test_existing_song_get_returns_200(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[self.song.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_song_returns_404(self):
        response = self.client.get(reverse("subekashi:song_delete", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_post_valid_reason_redirects(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        response = self.client.post(
            reverse("subekashi:song_delete", args=[self.song.id]),
            {"reason": "削除理由テスト"},
        )
        self.assertRedirects(
            response,
            f"/songs/{self.song.id}?toast=delete",
            fetch_redirect_response=False,
        )

    def test_post_empty_reason_returns_error(self):
        response = self.client.post(
            reverse("subekashi:song_delete", args=[self.song.id]),
            {"reason": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class EditorViewTest(TestCase):
    """EditorView (/editor/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.editor = Editor.objects.create(ip="127.0.0.4", is_open=True)

    def test_existing_editor_returns_200(self):
        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))
        self.assertEqual(response.status_code, 200)

    def test_author_history_links_to_author_page_not_deleted_message(self):
        author = Author.objects.create(name="編集者履歴テスト作者")
        History.create_for_author(
            author=author, title="別名を追加", history_type="edit", changes=None, editor=self.editor,
        )

        response = self.client.get(reverse("subekashi:editor", args=[self.editor.id]))

        self.assertContains(response, "編集者履歴テスト作者")
        self.assertNotContains(response, "この曲は削除されました")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorViewTest(TestCase):
    """AuthorView (/authors/<id>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="ビューテスト作者")
        song = Song.objects.create(title="作者ビューテスト曲")
        song.authors.add(self.author)

    def test_existing_author_returns_200(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_author_name_appears_in_response(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "ビューテスト作者")

    def test_alias_link_present_without_count_when_no_aliases(self):
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertNotContains(response, "件の別名")

    def test_alias_count_shown_when_forward_alias_exists(self):
        AuthorAlias.objects.create(name="件数テスト別名", author=self.author, alias_type="past")
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "1件の別名")

    def test_alias_count_includes_reverse_aliases(self):
        target = Author.objects.create(name="件数逆方向対象")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")
        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))
        self.assertContains(response, "1件の別名")

    def test_alias_count_reflects_transitive_count(self):
        # 件数表示はget_transitive_aliases()（#1005）の件数に合わせる（#1007）。
        # 自分から見て1ホップ(past)先の別名がさらに別名(spell)を持つ場合、
        # 2ホップ先の別名も件数に含まれる
        middle = Author.objects.create(name="件数中継作者")
        AuthorAlias.objects.create(name=middle.name, author=self.author, alias_type="past")
        AuthorAlias.objects.create(name="件数先端別名", author=middle, alias_type="spell")

        response = self.client.get(reverse("subekashi:author", args=[self.author.id]))

        self.assertContains(response, "2件の別名")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasesViewTest(TestCase):
    """AuthorAliasesView (/authors/<id>/aliases) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名一覧テスト作者")

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_no_aliases_returns_200(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "別名が見つかりませんでした")

    def test_forward_alias_is_displayed_with_edit_delete_links(self):
        alias = AuthorAlias.objects.create(name="別名X", author=self.author, alias_type="spell")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "別名X")
        self.assertContains(response, reverse("subekashi:author_alias_edit", args=[self.author.id, alias.id]))
        self.assertContains(response, reverse("subekashi:author_alias_delete", args=[self.author.id, alias.id]))

    def test_forward_alias_without_existing_author_shows_no_nav_icon(self):
        # 編集可能な行（自分が直接保有する別名）で、別名自体に対応する実在Authorが
        # 存在しない場合、遷移アイコンは表示しない（フォールバック先が自分自身になり
        # 無意味なため、編集可能な行では所有者へのフォールバックを行わない設計）
        AuthorAlias.objects.create(name="実在しない別名Y", author=self.author, alias_type="spell")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "実在しない別名Y")
        self.assertNotContains(response, "fa-arrow-right")

    def test_reverse_alias_is_displayed_without_edit_delete_links(self):
        target = Author.objects.create(name="別名逆方向対象")
        alias = AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "別名逆方向対象")
        self.assertNotContains(response, reverse("subekashi:author_alias_edit", args=[self.author.id, alias.id]))
        self.assertNotContains(response, reverse("subekashi:author_alias_delete", args=[self.author.id, alias.id]))

    def test_reverse_alias_shows_nav_icon_even_when_owner_id_is_zero(self):
        # 遷移先author idが0の場合でもアイコンが表示されることを確認する
        # （テンプレート側が`{% if row.next_alias_author_id %}`のような真偽値判定だと
        # 0がfalsyになり表示されなくなる。`is not None`で判定する必要がある）
        target = Author.objects.create(id=0, name="別名逆方向遷移対象ゼロ")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[target.id]))

    def test_reverse_alias_shows_nav_icon_to_owning_authors_list(self):
        # 編集・削除できない逆方向の別名は、代わりにその別名を所有するauthor自身の
        # 一覧画面への遷移アイコン(fa-arrow-right)を表示する
        target = Author.objects.create(name="別名逆方向遷移対象")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[target.id]))

    def test_forward_past_alias_shows_izen_no_meisho(self):
        # #1019: 正方向（自分がpastの別名を登録している側）は「以前の名称」のまま
        AuthorAlias.objects.create(name="以前の名称対象", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "以前の名称")
        self.assertNotContains(response, "その後の名称")

    def test_reverse_past_alias_shows_sonogo_no_meisho(self):
        # #1019: 逆方向（相手が自分をpastの別名として登録している側）は「その後の名称」と表示する
        target = Author.objects.create(name="その後の名称対象")
        AuthorAlias.objects.create(name=self.author.name, author=target, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "その後の名称")

    def test_past_alias_with_existing_author_links_to_channel(self):
        Author.objects.create(name="別名チャンネル対象")
        AuthorAlias.objects.create(name="別名チャンネル対象", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, reverse("subekashi:channel", args=["別名チャンネル対象"]))

    def test_past_alias_without_existing_author_does_not_link_to_channel(self):
        AuthorAlias.objects.create(name="実在しない別名", author=self.author, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertContains(response, "実在しない別名")
        self.assertNotContains(response, reverse("subekashi:channel", args=["実在しない別名"]))

    def test_non_linkable_alias_type_does_not_link_to_channel_even_if_author_exists(self):
        Author.objects.create(name="略称対象作者")
        AuthorAlias.objects.create(name="略称対象作者", author=self.author, alias_type="abbr")

        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))

        self.assertNotContains(response, reverse("subekashi:channel", args=["略称対象作者"]))

    def test_reload_button_present(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "reloadPage()")
        self.assertContains(response, "fa-redo")

    def test_add_button_has_plus_icon(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "fa-plus")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasesViewTransitiveResolutionTest(TestCase):
    """AuthorAliasesView の推移的関係解決の反映のテスト（#1007）

    #1003で確認された具体例（名義Aに別名義B・以前の名称C・以前の名称D・グループEを登録）を
    そのまま再現し、各authorの一覧画面が仕様表の通りになることを確認する。
    """

    def setUp(self):
        self.client = Client()
        self.a = Author.objects.create(name="view_tamura")
        self.b = Author.objects.create(name="view_inoue")
        self.c = Author.objects.create(name="view_kobayashi")
        self.d = Author.objects.create(name="view_yoshida")
        self.e = Author.objects.create(name="view_watanabe")
        self.alias_b = AuthorAlias.objects.create(name="view_inoue", author=self.a, alias_type="another")
        self.alias_c = AuthorAlias.objects.create(name="view_kobayashi", author=self.a, alias_type="past")
        self.alias_d = AuthorAlias.objects.create(name="view_yoshida", author=self.a, alias_type="past")
        self.alias_e = AuthorAlias.objects.create(name="view_watanabe", author=self.a, alias_type="group")

    def test_author_a_list_shows_four_direct_relations_all_editable(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.a.id]))

        self.assertContains(response, "view_inoue")
        self.assertContains(response, "別名義")
        self.assertContains(response, "view_kobayashi")
        self.assertContains(response, "view_yoshida")
        self.assertContains(response, "以前の名称")
        self.assertContains(response, "view_watanabe")
        self.assertContains(response, "所属グループ")
        # 4件とも自分が直接保有する別名のため、編集・削除リンクが4件分含まれる
        for alias in [self.alias_b, self.alias_c, self.alias_d, self.alias_e]:
            self.assertContains(response, reverse("subekashi:author_alias_edit", args=[self.a.id, alias.id]))
            self.assertContains(response, reverse("subekashi:author_alias_delete", args=[self.a.id, alias.id]))
        # 編集可能な行でも、別名自体(B/C/D/E)に対応する実在Authorへの遷移アイコンが表示される
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.b.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.c.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.d.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.e.id]))

    def test_author_b_list_shows_only_a_another_does_not_bridge(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.b.id]))

        self.assertContains(response, "view_tamura")
        self.assertContains(response, "別名義")
        self.assertNotContains(response, "view_kobayashi")
        self.assertNotContains(response, "view_yoshida")
        self.assertNotContains(response, "view_watanabe")
        # 逆方向のため編集・削除リンクは含まれない
        self.assertNotContains(response, "fa-pen")
        # Aへの関係は直接（1ホップ）だが逆方向で編集できないため、Aの一覧への遷移アイコンが表示される
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.a.id]))

    def test_author_c_list_shows_a_b_d_e_transitively_via_past(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.c.id]))

        self.assertContains(response, "view_tamura")
        self.assertContains(response, "view_inoue")
        self.assertContains(response, "view_yoshida")
        self.assertContains(response, "view_watanabe")
        self.assertContains(response, "所属グループ")
        # Aへの関係は逆方向のため「その後の名称」、Dへの関係は間接的だが正方向のため「以前の名称」のまま（#1019）
        self.assertContains(response, "その後の名称")
        self.assertContains(response, "以前の名称")
        # Aへの関係は逆方向、B/D/Eへの関係は間接的なため、いずれも編集・削除できない
        self.assertNotContains(response, "fa-pen")
        # 編集できない4件（A・B・D・E）全てに、それぞれの別名一覧への遷移アイコンが表示される
        # （ホップ数・方向を問わず、対応するAuthorが実在すれば表示する）
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.a.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.b.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.d.id]))
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.e.id]))

    def test_author_c_list_query_count_is_bounded(self):
        # #1023: 遷移先author idの補完的な問い合わせが、クラスタ全体ではなく
        # 未解決の名前(B・E)のみを対象にした1クエリに収まっていることの回帰防止テスト。
        # クエリ数が増えた場合はこの値を更新しつつ、原因を確認すること
        # （10クエリ目は#1008で追加した一番有名な名義の候補一覧取得）
        with self.assertNumQueries(10):
            self.client.get(reverse("subekashi:author_aliases", args=[self.c.id]))

    def test_author_c_list_unresolved_query_scope_excludes_resolved_names(self):
        # #1023: 補完的な問い合わせのIN句が、get_transitive_aliases()側で既に
        # author_idを解決済みのA・D（別名一覧に4件とも表示されるが、A・Dはauthor_idが
        # 解決済みのため対象外になるはず）を含まず、未解決のB・Eのみに絞られていることを
        # 直接確認する（クエリ数だけではクラスタ全体を対象にする regression を検知できないため）
        with CaptureQueriesContext(connection) as ctx:
            self.client.get(reverse("subekashi:author_aliases", args=[self.c.id]))

        unresolved_queries = [
            q for q in ctx.captured_queries
            if 'subekashi_author"."name" IN' in q["sql"]
        ]
        self.assertEqual(len(unresolved_queries), 1)
        sql = unresolved_queries[0]["sql"]
        self.assertIn("view_inoue", sql)
        self.assertIn("view_watanabe", sql)
        self.assertNotIn("view_tamura", sql)
        self.assertNotIn("view_yoshida", sql)

    def test_author_e_list_shows_only_a_group_does_not_bridge(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.e.id]))

        self.assertContains(response, "view_tamura")
        self.assertContains(response, "所属している名義")
        self.assertNotContains(response, "view_inoue")
        self.assertNotContains(response, "view_kobayashi")
        self.assertNotContains(response, "view_yoshida")
        self.assertNotContains(response, "fa-pen")
        # Aへの関係は直接（1ホップ）だが逆方向で編集できないため、Aの一覧への遷移アイコンが表示される
        self.assertContains(response, "fa-arrow-right")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[self.a.id]))

    def test_alias_without_existing_author_falls_back_to_owner_nav_icon(self):
        # 別名自体(ghost)に対応する実在Authorが存在しない場合でも、編集できない行は
        # そのAuthorAlias自体を実際に所有しているauthor(p)のページへフォールバックする。
        # p→ghost(past、Authorなし)、p→r(past、rは実在) という構成でrの一覧を見ると、
        # pへの関係(直接・逆方向)もghostへの関係(間接)も、どちらもpのページへ遷移する
        p = Author.objects.create(name="view_nav_p")
        r = Author.objects.create(name="view_nav_r")
        AuthorAlias.objects.create(name="view_nav_ghost", author=p, alias_type="past")
        AuthorAlias.objects.create(name=r.name, author=p, alias_type="past")

        response = self.client.get(reverse("subekashi:author_aliases", args=[r.id]))

        self.assertContains(response, "view_nav_ghost")
        self.assertContains(response, "view_nav_p")
        self.assertContains(response, reverse("subekashi:author_aliases", args=[p.id]))
        # p自身の行、ghostのフォールバック行の2件分の遷移アイコンが表示される
        self.assertEqual(response.content.decode().count("fa-arrow-right"), 2)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasNewViewTest(TestCase):
    """AuthorAliasNewView (/authors/<id>/aliases/new) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名新規テスト作者")

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertEqual(response.status_code, 200)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_alias_type_has_placeholder_option(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, '<option value="" selected disabled>選択してください</option>')

    def test_alias_type_options_have_description_attribute(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, 'data-description="以前使用されていた名称です。')

    def test_linkable_alias_types_mention_channel_link_in_description(self):
        # past/another/groupはchannelリンクが貼られる種別のため、説明文にその旨を含める
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        past_option = content[content.index('value="past"'):content.index('</option>', content.index('value="past"'))]
        another_option = content[content.index('value="another"'):content.index('</option>', content.index('value="another"'))]
        group_option = content[content.index('value="group"'):content.index('</option>', content.index('value="group"'))]
        abbr_option = content[content.index('value="abbr"'):content.index('</option>', content.index('value="abbr"'))]
        self.assertIn("チャンネルページへのリンク", past_option)
        self.assertIn("チャンネルページへのリンク", another_option)
        self.assertIn("チャンネルページへのリンク", group_option)
        self.assertNotIn("チャンネルページへのリンク", abbr_option)

    def test_group_option_is_available(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, 'value="group"')
        self.assertContains(response, "グループ</option>")

    def test_another_description_mentions_official_recognition(self):
        # 別名義は本人による公認が前提であることを説明文に明記する
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        another_option = content[content.index('value="another"'):content.index('</option>', content.index('value="another"'))]
        self.assertIn("公認", another_option)

    def test_submit_button_initially_disabled(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, '<input type="submit" value="登録" disabled>')

    def test_alias_type_description_has_info_icon_between_form_and_button(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        content = response.content.decode()
        self.assertContains(response, "fas fa-info-circle info")
        self.assertContains(response, 'id="alias-type-description-text"')
        # 説明欄がフォームのフィールド群より後、送信ボタンより前にあることを確認する
        description_index = content.index('id="alias-type-description"')
        select_index = content.index('id="alias_type"')
        submit_index = content.index('<input type="submit"')
        self.assertLess(select_index, description_index)
        self.assertLess(description_index, submit_index)

    def test_includes_author_alias_form_js(self):
        response = self.client.get(reverse("subekashi:author_alias_new", args=[self.author.id]))
        self.assertContains(response, "author_alias_form.js")

    def test_post_creates_alias_and_redirects_to_list(self):
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "新規別名A", "alias_type": "past"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=new"
        )
        self.assertTrue(AuthorAlias.objects.filter(name="新規別名A", author=self.author).exists())

    def test_post_creates_history(self):
        self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "新規別名B", "alias_type": "past"},
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "new")
        self.assertIn("新規別名B", history.title)

    def test_post_duplicate_name_shows_error_without_creating(self):
        AuthorAlias.objects.create(name="重複別名", author=self.author)
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "重複別名", "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(AuthorAlias.objects.filter(name="重複別名").count(), 1)

    def test_post_name_same_as_author_shows_error(self):
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": self.author.name, "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(AuthorAlias.objects.filter(name=self.author.name).exists())

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "通知別名", "alias_type": "past"},
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("通知別名", content)
        self.assertIn(self.author.name, content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_rolls_back_alias_and_returns_500(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_alias_new", args=[self.author.id]),
            {"name": "通知失敗別名", "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertFalse(AuthorAlias.objects.filter(name="通知失敗別名").exists())
        # Discord通知前にはDBへ一切書き込まないため、孤立したHistoryも作成されない
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    def test_toctou_duplicate_name_shows_friendly_error_not_500(self):
        # フォームのclean_name()での重複チェックをすり抜けた場合でも、
        # DB制約(IntegrityError)を捕捉してフォームエラーに変換されることを確認する
        AuthorAlias.objects.create(name="競合別名", author=self.author)
        with patch.object(AuthorAliasForm, "clean_name", return_value="競合別名"):
            response = self.client.post(
                reverse("subekashi:author_alias_new", args=[self.author.id]),
                {"name": "競合別名", "alias_type": "past"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "その別名は既に登録されています。")
        self.assertEqual(AuthorAlias.objects.filter(name="競合別名").count(), 1)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasEditViewTest(TestCase):
    """AuthorAliasEditView (/authors/<id>/aliases/<alias_id>/edit) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名編集テスト作者")
        self.alias = AuthorAlias.objects.create(name="編集前別名", author=self.author, alias_type="past")

    def test_get_returns_200(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_current_alias_type_is_selected(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, 'value="past" data-description="以前使用されていた名称です。')
        self.assertContains(response, 'selected>以前の名称</option>')

    def test_alias_type_has_disabled_placeholder_option(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, '<option value="" disabled>選択してください</option>')

    def test_includes_author_alias_form_js(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, "author_alias_form.js")

    def test_nonexistent_alias_returns_404(self):
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[self.author.id, 99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_alias_belonging_to_other_author_returns_404(self):
        other_author = Author.objects.create(name="別の作者")
        response = self.client.get(
            reverse("subekashi:author_alias_edit", args=[other_author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 404)

    def test_post_updates_alias_and_redirects_to_list(self):
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後別名", "alias_type": "sns"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=edit"
        )
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集後別名")
        self.assertEqual(self.alias.alias_type, "sns")

    def test_post_creates_history(self):
        self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後別名2", "alias_type": "sns"},
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "edit")
        self.assertIn("編集前別名", history.title)

    def test_post_can_keep_own_name_unchanged(self):
        # 自分自身(編集対象)の現在の名前のまま更新しても重複エラーにならない
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集前別名", "alias_type": "sns"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=edit"
        )

    def test_post_duplicate_name_with_other_alias_shows_error(self):
        AuthorAlias.objects.create(name="他の別名", author=self.author)
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "他の別名", "alias_type": "past"},
        )
        self.assertEqual(response.status_code, 200)
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集前別名")

    def test_post_without_actual_change_skips_history(self):
        # SongEditViewと同様、実質的な変更がない場合は履歴を作成しない
        before_count = History.get_for_author(self.author).count()
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集前別名", "alias_type": "past"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=edit"
        )
        self.assertEqual(History.get_for_author(self.author).count(), before_count)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_without_actual_change_does_not_send_discord(self, mock_send_discord):
        self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集前別名", "alias_type": "past"},
        )
        self.assertFalse(mock_send_discord.called)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_with_change_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後通知別名", "alias_type": "sns"},
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("編集後通知別名", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_returns_500(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
            {"name": "編集後失敗別名", "alias_type": "sns"},
        )
        self.assertEqual(response.status_code, 500)
        # Discord通知失敗時はDBへコミットしないため、editが実際には成功してしまわないこと・
        # 孤立したHistoryが残らないことを確認する
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集前別名")
        self.assertEqual(self.alias.alias_type, "past")
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    def test_toctou_duplicate_name_shows_friendly_error_not_500(self):
        AuthorAlias.objects.create(name="編集競合別名", author=self.author)
        with patch.object(AuthorAliasForm, "clean_name", return_value="編集競合別名"):
            response = self.client.post(
                reverse("subekashi:author_alias_edit", args=[self.author.id, self.alias.id]),
                {"name": "編集競合別名", "alias_type": "past"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "その別名は既に登録されています。")
        self.alias.refresh_from_db()
        self.assertEqual(self.alias.name, "編集前別名")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorAliasDeleteViewTest(TestCase):
    """AuthorAliasDeleteView (/authors/<id>/aliases/<alias_id>/delete) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="別名削除テスト作者")
        self.alias = AuthorAlias.objects.create(name="削除対象別名", author=self.author, alias_type="past")

    def test_get_returns_200(self):
        response = self.client.get(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "削除対象別名")

    def test_cancel_and_delete_buttons_have_icons(self):
        response = self.client.get(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertContains(response, "fa-times")
        self.assertContains(response, "fa-trash-alt")

    def test_nonexistent_alias_returns_404(self):
        response = self.client.get(
            reverse("subekashi:author_alias_delete", args=[self.author.id, 99999])
        )
        self.assertEqual(response.status_code, 404)

    def test_post_deletes_alias_and_redirects_to_list(self):
        response = self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=delete"
        )
        self.assertFalse(AuthorAlias.objects.filter(pk=self.alias.id).exists())

    def test_post_creates_history_and_preserves_author_link(self):
        self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "delete")
        self.assertIn("削除対象別名", history.title)
        self.assertEqual(history.author, self.author)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("削除対象別名", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_prevents_deletion(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_alias_delete", args=[self.author.id, self.alias.id])
        )
        self.assertEqual(response.status_code, 500)
        self.assertTrue(AuthorAlias.objects.filter(pk=self.alias.id).exists())
        self.assertEqual(History.get_for_author(self.author).count(), 0)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AuthorPrimaryNameSetViewTest(TestCase):
    """AuthorPrimaryNameSetView (/authors/<id>/aliases/primary) のテスト（#1008）"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="現在の名義")
        self.past_alias = AuthorAlias.objects.create(name="以前の名義", author=self.author, alias_type="past")

    def test_nonexistent_author_returns_404(self):
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[99999]), {"name": "以前の名義"}
        )
        self.assertEqual(response.status_code, 404)

    def test_selecting_current_name_is_noop_and_redirects(self):
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": self.author.name},
        )
        self.assertRedirects(response, reverse("subekashi:author_aliases", args=[self.author.id]))
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")

    def test_selecting_past_alias_swaps_name_and_reregisters_old_name_as_past(self):
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "以前の名義")
        # 選ばれた側の別名行は消え、旧名が新たなpast別名として登録される
        self.assertFalse(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        new_alias = AuthorAlias.objects.get(name="現在の名義")
        self.assertEqual(new_alias.author, self.author)
        self.assertEqual(new_alias.alias_type, "past")

    def test_selecting_non_past_alias_type_is_rejected(self):
        AuthorAlias.objects.create(name="別名義候補", author=self.author, alias_type="another")
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "別名義候補"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")

    def test_selecting_name_conflicting_with_another_author_is_rejected(self):
        Author.objects.create(name="以前の名義")
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())

    def test_post_creates_history_with_before_and_after_names(self):
        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        history = History.get_for_author(self.author).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.history_type, "edit")
        self.assertIn("以前の名義", history.title)
        self.assertEqual(history.changes[1], ["一番有名な名義", "現在の名義", "以前の名義"])

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_sends_discord_notification(self, mock_send_discord):
        mock_send_discord.return_value = True
        self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertTrue(mock_send_discord.called)
        content = mock_send_discord.call_args[0][1]
        self.assertIn("現在の名義", content)
        self.assertIn("以前の名義", content)

    @patch("subekashi.views.author_alias.send_discord")
    def test_post_discord_failure_prevents_name_change(self, mock_send_discord):
        mock_send_discord.return_value = False
        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )
        self.assertEqual(response.status_code, 500)
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    @patch("subekashi.views.author_alias.send_discord")
    def test_alias_deleted_concurrently_during_discord_wait_redirects_with_error(self, mock_send_discord):
        # send_discord()（ネットワークI/O）の完了を待つ間に、別のリクエストが対象の
        # past別名を削除してしまうケースを、send_discordのside_effectで模擬する。
        # DoesNotExistが未処理の例外(500)にならず、他の異常系と同じくtoast=primary_error
        # へ穏当にリダイレクトされることを確認する
        def delete_alias_then_succeed(url, content):
            self.past_alias.delete()
            return True

        mock_send_discord.side_effect = delete_alias_then_succeed

        response = self.client.post(
            reverse("subekashi:author_primary_name_set", args=[self.author.id]),
            {"name": "以前の名義"},
        )

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertEqual(History.get_for_author(self.author).count(), 0)

    def test_old_name_conflicting_with_existing_alias_is_rejected_before_discord(self):
        # AuthorAlias.nameはグローバルにuniqueなため、旧名(old_name)が既に別のauthorの
        # 別名として登録されている場合、以前の名称として再登録できずIntegrityErrorになる。
        # これは同時実行のレースではなく既存データ次第で毎回決定的に失敗するため、
        # Discord通知を送る前に弾く（通知だけ成功してDBが更新されない不整合を避ける）
        other = Author.objects.create(name="別の作者")
        AuthorAlias.objects.create(name=self.author.name, author=other, alias_type="another")

        with patch("subekashi.views.author_alias.send_discord") as mock_send_discord:
            response = self.client.post(
                reverse("subekashi:author_primary_name_set", args=[self.author.id]),
                {"name": "以前の名義"},
            )
            self.assertFalse(mock_send_discord.called)

        self.assertRedirects(
            response, reverse("subekashi:author_aliases", args=[self.author.id]) + "?toast=primary_error"
        )
        self.author.refresh_from_db()
        self.assertEqual(self.author.name, "現在の名義")
        self.assertTrue(AuthorAlias.objects.filter(pk=self.past_alias.pk).exists())

    def test_alias_list_page_shows_primary_name_form_when_past_alias_exists(self):
        response = self.client.get(reverse("subekashi:author_aliases", args=[self.author.id]))
        self.assertContains(response, "primary-name-form")
        self.assertContains(response, "一番有名な名義")

    def test_alias_list_page_hides_primary_name_form_when_no_past_alias(self):
        author = Author.objects.create(name="別名なし作者")
        response = self.client.get(reverse("subekashi:author_aliases", args=[author.id]))
        self.assertNotContains(response, "primary-name-form")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class ChannelViewTest(TestCase):
    """ChannelView (/channel/<name>/) のテスト"""

    def setUp(self):
        self.client = Client()
        self.author = Author.objects.create(name="チャンネルリダイレクト作者")

    def test_existing_author_redirects(self):
        response = self.client.get(
            reverse("subekashi:channel", args=["チャンネルリダイレクト作者"])
        )
        self.assertEqual(response.status_code, 302)

    def test_redirect_destination_is_author_page(self):
        response = self.client.get(
            reverse("subekashi:channel", args=["チャンネルリダイレクト作者"])
        )
        expected_url = reverse("subekashi:author", args=[self.author.id])
        self.assertRedirects(response, expected_url)

    def test_nonexistent_author_returns_404(self):
        response = self.client.get(
            reverse("subekashi:channel", args=["存在しない作者名XYZ"])
        )
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class ContactViewTest(TestCase):
    """ContactView (/contact/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:contact"))
        self.assertEqual(response.status_code, 200)

    def test_post_valid_form_returns_ok(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        response = self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告", "detail": "テスト詳細文"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result"], "ok")

    def test_post_valid_form_creates_contact_record(self):
        # 自動登録によりContactレコードが作成されること
        self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告", "detail": "テスト詳細文"},
        )
        self.assertTrue(Contact.objects.filter(detail="テスト詳細文").exists())

    def test_post_invalid_form_returns_error(self):
        # detail が未入力の場合はフォームバリデーションエラー
        response = self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("入力必須項目", response.context["result"])

    def test_post_invalid_form_does_not_create_contact_record(self):
        count_before = Contact.objects.count()
        self.client.post(
            reverse("subekashi:contact"),
            {"category": "不具合の報告"},
        )
        self.assertEqual(Contact.objects.count(), count_before)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class HistoriesViewTest(TestCase):
    """HistoriesView (/histories/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:histories"))
        self.assertEqual(response.status_code, 200)

    def test_author_history_links_to_author_page_not_deleted_message(self):
        # author向けのHistory(song=None)が「この曲は削除されました」と誤表示されないことを確認する
        editor = Editor.objects.create(ip="127.0.0.2")
        author = Author.objects.create(name="履歴一覧テスト作者")
        History.create_for_author(
            author=author, title="別名を追加", history_type="edit", changes=None, editor=editor,
        )

        response = self.client.get(reverse("subekashi:histories"))

        self.assertContains(response, "履歴一覧テスト作者")
        self.assertNotContains(response, "この曲は削除されました")

    def test_author_deleted_after_history_shows_deleted_message(self):
        editor = Editor.objects.create(ip="127.0.0.3")
        author = Author.objects.create(name="削除される作者")
        History.create_for_author(
            author=author, title="作者削除", history_type="delete", changes=["理由", "テスト"], editor=editor,
        )
        author.delete()

        response = self.client.get(reverse("subekashi:histories"))

        self.assertContains(response, "この曲または作者は削除されました")


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE, RATELIMIT_ENABLE=False)
class SongCardsViewTest(TestCase):
    """SongCardsView (/api/html/song_cards) のテスト"""

    def setUp(self):
        self.client = Client()
        Song.objects.create(title="カードテスト曲", lyrics="歌詞")

    def test_sort_upload_time_shows_search_info(self):
        """sort=upload_time のとき「YouTubeの曲を表示しています」が含まれること"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "upload_time"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("YouTubeの曲を表示しています", content)

    def test_sort_minus_upload_time_shows_search_info(self):
        """sort=-upload_time のとき「YouTubeの曲を表示しています」が含まれること"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "-upload_time"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("YouTubeの曲を表示しています", content)

    def test_no_sort_does_not_show_upload_time_search_info(self):
        """sort指定なしのとき投稿日用のsearch-infoが含まれないこと"""
        response = self.client.get(reverse("subekashi:song_cards"))
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertNotIn("YouTubeの曲を表示しています", content)

    def test_other_sort_does_not_show_upload_time_search_info(self):
        """sort=title のとき投稿日用のsearch-infoが含まれないこと"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"sort": "title"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertNotIn("YouTubeの曲を表示しています", content)

    def test_questionable_song_card_hides_lyrics(self):
        """is_questionable=True の曲のカードには .song-card-lyrics が含まれないこと"""
        Song.objects.create(title="界隈曲カードテスト", is_questionable=True)
        response = self.client.get(
            reverse("subekashi:song_cards"), {"keyword": "界隈曲カードテスト"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertNotIn("song-card-lyrics", content)

    def test_normal_song_card_shows_lyrics(self):
        """is_questionable=False の曲のカードには .song-card-lyrics が含まれること"""
        response = self.client.get(
            reverse("subekashi:song_cards"), {"keyword": "カードテスト曲"}
        )
        self.assertEqual(response.status_code, 200)
        content = "".join(response.json())
        self.assertIn("song-card-lyrics", content)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class RedirectViewTest(TestCase):
    """/search/ と /new/ のリダイレクトテスト"""

    def setUp(self):
        self.client = Client()

    def test_search_redirects_to_songs(self):
        response = self.client.get("/search/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/songs/", fetch_redirect_response=False)

    def test_new_redirects_to_songs_new(self):
        response = self.client.get("/new/")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/songs/new/", fetch_redirect_response=False)


@override_settings(STATICFILES_STORAGE=STATIC_STORAGE)
class AdViewTest(TestCase):
    """AdView (/ad/) のテスト"""

    def setUp(self):
        self.client = Client()

    def test_get_returns_200(self):
        response = self.client.get(reverse("subekashi:ad"))
        self.assertEqual(response.status_code, 200)

    def test_post_with_unregistered_previous_ad_does_not_error(self):
        """
        cookieに残った旧宣伝URLがAdレコードとして存在しない場合でも
        AttributeErrorにならず正常に処理されること（Issue #985）
        """
        previous_ad_url = "https://www.youtube.com/watch?v=aaaaaaaaaaa"
        response = self.client.post(
            reverse("subekashi:ad"),
            {
                "url1": "",
                "ad1": previous_ad_url,
                "url2": "",
                "ad2": "",
                "url3": "",
                "ad3": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("subekashi:ad_complete"))

    def test_post_valid_new_ad_redirects_and_increments_dup(self):
        # SEND_DISCORD=False のため send_discord は即 True を返す
        new_ad_url = "https://www.youtube.com/watch?v=bbbbbbbbbbb"
        response = self.client.post(
            reverse("subekashi:ad"),
            {
                "url1": new_ad_url,
                "ad1": "",
                "url2": "",
                "ad2": "",
                "url3": "",
                "ad3": "",
            },
        )
        self.assertRedirects(response, reverse("subekashi:ad_complete"))
        adIns = Ad.objects.get(url="https://youtu.be/bbbbbbbbbbb")
        self.assertEqual(adIns.dup, 1)
