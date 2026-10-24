"""
lib/timeline_import.py のテスト（すべあな界隈年表から曲を登録・更新する、#52）

モチーフ列から模倣元のタイトルを取り出す処理と、年表の行から曲を新規作成・更新する処理を検証する。
行のURL（URL列・URL2列）が登録されている曲を更新し、どのURLも登録されていなければ新規作成する。
どのURLも登録されていなくても、歌詞列の曲とタイトルか作者が一致すればその曲を更新する。
タイトル・作者は更新せず、URL・模倣は追加のみ、カテゴリは年表の値にする。Historyの編集者はid=1のEditor。
"""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase

from subekashi.lib.timeline import TimelineRow
from subekashi.lib.timeline_import import (
    get_author_names,
    get_motif1_title,
    get_motif2_titles,
    get_song_urls,
    import_timeline,
)
from subekashi.models import Author, Editor, History, Prush, Song, SongLink


def make_row(**fields):
    values = {
        "year": 2024, "row": 2, "date": None, "premiere_rush": "", "title": "曲", "author": "作者", "badge": "",
        "category": "曲", "motif1": "", "motif2": "", "urls": ["https://youtu.be/aaaaaaaaaaa"], "decode_date": "",
        "decode_urls": [], "lyrics_url": "", "distribution": "", "distribution2": "", "distribution_urls": [], "notes": [],
    }
    values.update(fields)
    return TimelineRow(**values)


def create_song(title, author="作者", urls=(), **fields):
    song = Song.objects.create(title=title, **fields)
    song.authors.add(Author.objects.get_or_create(name=author)[0])
    for url in urls:
        SongLink.objects.get_or_create(url=url)[0].songs.add(song)
    return song


def song_urls(song):
    return list(song.links.order_by("id").values_list("url", flat=True))


class GetMotifTitleTest(SimpleTestCase):
    def test_motif1_removes_waku(self):
        self.assertEqual(get_motif1_title("教育枠"), "教育")
        self.assertEqual(get_motif1_title(".[short]枠"), ".[short]")
        self.assertEqual(get_motif1_title("本家以外模倣"), "本家以外模倣")
        self.assertEqual(get_motif1_title(""), "")

    def test_motif2_arrow_form(self):
        # 先頭の矢印を除き、末尾の作者のバッジ（絵文字1文字分）を削る前と後の順に候補にする
        self.assertEqual(get_motif2_titles("→.[short]👤"), [".[short]👤", ".[short]"])
        self.assertEqual(get_motif2_titles("→0⁰🔩"), ["0⁰🔩", "0⁰"])
        self.assertEqual(get_motif2_titles("→春ノ海"), ["春ノ海"])
        # 異体字セレクタ付きの絵文字・ZWJで繋がった絵文字も1文字分
        self.assertEqual(get_motif2_titles("→曲🌧️")[-1], "曲")
        self.assertEqual(get_motif2_titles("→曲👨‍👩‍👧")[-1], "曲")
        # 1文字分を削った候補の後に、作者のバッジ（絵文字と「+」）を全て削った候補を加える（合作の曲）
        self.assertEqual(get_motif2_titles("→曲🍁🔩"), ["曲🍁🔩", "曲🍁", "曲"])
        self.assertEqual(get_motif2_titles("→生合成🔢😥"), ["生合成🔢😥", "生合成🔢", "生合成"])
        self.assertEqual(get_motif2_titles("→天秤にかけて🍁+"), ["天秤にかけて🍁+", "天秤にかけて"])
        # 末尾が絵文字でない記号は削らない
        self.assertEqual(get_motif2_titles("→曲^"), ["曲^"])
        # 記号1文字のタイトル（削ると空になる）
        self.assertEqual(get_motif2_titles("→❁"), ["❁"])

    def test_motif2_imitate_form(self):
        # 末尾の「模倣」と、その前の作者のバッジ（絵文字と「+」）を削る前と後の順に候補にする
        self.assertEqual(get_motif2_titles("鵺🔢模倣"), ["鵺🔢模倣", "鵺🔢", "鵺"])
        self.assertEqual(get_motif2_titles("天秤にかけて🍁+模倣")[-1], "天秤にかけて")
        self.assertEqual(get_motif2_titles("蝕🍁🌌🌧️模倣")[-1], "蝕")
        self.assertEqual(get_motif2_titles("᠈[short]📺️模倣")[-1], "᠈[short]")
        # 「模倣」で終わるタイトル
        self.assertEqual(get_motif2_titles("全てが適当すぎた.模倣"), ["全てが適当すぎた.模倣", "全てが適当すぎた."])

    def test_motif2_without_arrow(self):
        self.assertEqual(get_motif2_titles("名の無い星"), ["名の無い星"])
        self.assertEqual(get_motif2_titles("K²🔩"), ["K²🔩", "K²"])
        self.assertEqual(get_motif2_titles(""), [])


class GetAuthorNamesTest(SimpleTestCase):
    def test_splits_lines(self):
        self.assertEqual(get_author_names("作者"), ["作者"])
        # 合作は改行で区切り、2人目以降の先頭に「+」が付くことがある
        self.assertEqual(get_author_names("作者A\n+作者B"), ["作者A", "作者B"])
        # 「+」で始まる作者もいるため、1人目の「+」は削らない
        self.assertEqual(get_author_names("+SSBA"), ["+SSBA"])
        self.assertEqual(get_author_names("+SSBA\n+作者B"), ["+SSBA", "作者B"])
        self.assertEqual(get_author_names("作者A \n\n作者B"), ["作者A", "作者B"])
        # 「、」「/」は名前の一部として使われているため区切らない
        self.assertEqual(get_author_names("全て魚の所為で、"), ["全て魚の所為で、"])
        self.assertEqual(get_author_names("あんくらげ / Ankurage"), ["あんくらげ / Ankurage"])
        # 空白文字のみの作者名はそのまま返す
        self.assertEqual(get_author_names("\u3000"), ["\u3000"])
        self.assertEqual(get_author_names(""), [])


class GetSongUrlsTest(SimpleTestCase):
    def test_cleans_and_filters_urls(self):
        urls = get_song_urls([
            "https://www.youtube.com/watch?v=aaaaaaaaaaa&t=91s",
            "https://m.youtube.com/watch?v=aaaaaaaaaaa",
            "https://www.nicovideo.jp/watch/sm1",
            "https://twitter.com/user/status/1?s=20",
            # ライブのURLは短縮URLにする
            "https://www.youtube.com/live/bbbbbbbbbbb?si=xxxx",
            # 「https://」の無いURL
            "youtu.be/ccccccccccc",
            # 登録できないURL
            "https://www.youtube.com/post/Ugz2NFeQm6RobFzqwPB4AaABCQ",
            "https://discord.com/channels/1/2/3",
            ".be/ddddddddddd",
            "DSC_0006.avi - ニコニコ動画",
            "https://nicovideo.jp/watch/" + "a" * 300,
        ])

        self.assertEqual(urls, [
            "https://youtu.be/aaaaaaaaaaa", "https://nicovideo.jp/watch/sm1", "https://x.com/user/status/1",
            "https://youtu.be/bbbbbbbbbbb", "https://youtu.be/ccccccccccc",
        ])


@patch.dict("sys.modules", {"subekashi.constants.dynamic.reject": MagicMock(REJECT_LIST=["掲載拒否の作者"])})
class ImportTimelineTest(TestCase):
    def setUp(self):
        self.editor = Editor.objects.create(pk=1, ip="")
        Author.objects.create(pk=1, name="全てあなたの所為です。")

    def test_creates_song(self):
        education = create_song("教育", "全てあなたの所為です。")
        k2 = create_song("K²", "全てあなたの所為です。")
        result = import_timeline([make_row(
            title="新しい曲", author="作者A\n作者B", category="DSC", motif1="教育枠", motif2="→K²🔩",
            urls=["https://www.youtube.com/watch?v=aaaaaaaaaaa", "https://www.nicovideo.jp/watch/sm1"],
        )])

        song = Song.objects.get(title="新しい曲")
        self.assertEqual(result.created, [song])
        self.assertEqual(sorted(song.authors.values_list("name", flat=True)), ["作者A", "作者B"])
        self.assertEqual(song.category, "song")
        self.assertEqual(song_urls(song), ["https://youtu.be/aaaaaaaaaaa", "https://nicovideo.jp/watch/sm1"])
        self.assertEqual(set(song.imitates.all()), {education, k2})

        history = song.histories.get()
        self.assertEqual(history.editor, self.editor)
        self.assertEqual(history.history_type, "new")
        self.assertEqual(history.title, "新しい曲を新規作成")
        self.assertIn(["URL", "https://youtu.be/aaaaaaaaaaa,https://nicovideo.jp/watch/sm1"], history.changes)
        self.assertIn(["カテゴリ", "曲"], history.changes)
        self.assertIn(["模倣", "教育\nK²"], history.changes)

    def test_category_map(self):
        cases = {
            "曲": "song", "DSC": "song", "逆再生枠": "song", "アレンジ": "arrange", "音mad": "otomad",
            "メドレー": "medley", "総集編": "omnibus", "予告": "notice", "オフボ": "offv", "カバー": "cover", "ネタ": "meme",
            "": "song",
        }
        rows = [
            make_row(title=f"カテゴリ{category}", category=category, urls=[f"https://www.nicovideo.jp/watch/sm{i}"])
            for i, category in enumerate(cases)
        ]
        import_timeline(rows)

        for category, value in cases.items():
            with self.subTest(category=category):
                self.assertEqual(Song.objects.get(title=f"カテゴリ{category}").category, value)

    def test_excluded_categories_are_not_imported(self):
        rows = [
            make_row(category=category, urls=[f"https://www.nicovideo.jp/watch/sm{i}"])
            for i, category in enumerate(["解読", "その他", "配信", "企画", "出来事", "不明"])
        ]
        result = import_timeline(rows)

        self.assertEqual(result.excluded, 6)
        self.assertEqual(result.unknown_categories, [])
        self.assertFalse(Song.objects.exists())

    def test_unknown_category_is_reported(self):
        row = make_row(category="新カテゴリ")
        result = import_timeline([row])

        self.assertEqual(result.unknown_categories, [row])
        self.assertFalse(Song.objects.exists())

    def test_skips_rows_without_song_urls(self):
        rows = [
            make_row(urls=[]),
            make_row(urls=["https://discord.com/channels/1/2/3"]),
            make_row(urls=["https://www.youtube.com/post/Ugz2NFeQm6RobFzqwPB4AaABCQ"]),
        ]
        result = import_timeline(rows)

        # URLで照合できず、毎日新規作成されてしまうため登録しない
        self.assertEqual([reason for _, reason in result.skipped], ["登録できるURLが無い"] * 3)
        self.assertFalse(Song.objects.exists())

    def test_skips_new_song_with_invalid_title_or_author(self):
        rows = [
            make_row(title=""),
            make_row(title="a" * 501),
            make_row(author=""),
            make_row(author="a" * 256),
            make_row(author="作者\n掲載拒否の作者"),
        ]
        result = import_timeline(rows)

        self.assertEqual(
            [reason for _, reason in result.skipped],
            ["タイトルが空", "タイトルが長すぎる", "作者が空", "作者名が長すぎる", "掲載拒否の作者"],
        )
        self.assertFalse(Song.objects.exists())
        # 掲載拒否の作者の行で作った作者は残さない
        self.assertFalse(Author.objects.filter(name__in=["作者", "掲載拒否の作者"]).exists())

    def test_creates_song_with_whitespace_only_title_and_author(self):
        # 0文字でなければ、空白文字のみのタイトル・作者でも登録する
        result = import_timeline([make_row(title="\u3000", author="\t")])

        song = result.created[0]
        self.assertEqual(song.title, "\u3000")
        self.assertEqual(song.authors_str(), "\t")

    def test_skips_url_of_deleted_song(self):
        # deleteコマンドで削除した曲のURL（is_removed=True）は、再び登録しない
        SongLink.objects.create(url="https://youtu.be/aaaaaaaaaaa", is_removed=True)
        result = import_timeline([make_row()])

        self.assertEqual([reason for _, reason in result.skipped], ["削除された曲のURL"])
        self.assertFalse(Song.objects.exists())

    def test_reuses_link_without_songs(self):
        link = SongLink.objects.create(url="https://youtu.be/aaaaaaaaaaa")
        import_timeline([make_row()])

        self.assertEqual(list(link.songs.all()), [Song.objects.get(title="曲")])
        self.assertEqual(SongLink.objects.count(), 1)

    def test_updates_song(self):
        aaa = create_song("AAA", "原曲の作者")
        bbb = create_song("BBB", "原曲の作者")
        ccc = create_song("CCC", "原曲の作者")
        song = create_song("曲", "作者", ["https://youtu.be/AAAAAAAAAAC", "https://youtu.be/AAAAAAAAAAB"])
        song.imitates.add(aaa, ccc)
        post_time = song.post_time

        result = import_timeline([make_row(
            title="年表のタイトル", author="年表の作者", category="カバー", motif1="AAA", motif2="→BBB",
            urls=["https://youtu.be/AAAAAAAAAAA", "https://youtu.be/AAAAAAAAAAB"],
        )])

        song.refresh_from_db()
        self.assertEqual(result.created, [])
        self.assertEqual(result.updated[0][0], song)
        # タイトル・作者は更新しない
        self.assertEqual(song.title, "曲")
        self.assertEqual(song.authors_str(), "作者")
        self.assertEqual(song.category, "cover")
        self.assertEqual(
            song_urls(song),
            ["https://youtu.be/AAAAAAAAAAC", "https://youtu.be/AAAAAAAAAAB", "https://youtu.be/AAAAAAAAAAA"],
        )
        self.assertEqual(set(song.imitates.all()), {aaa, bbb, ccc})
        self.assertGreater(song.post_time, post_time)

        history = song.histories.get()
        self.assertEqual(history.editor, self.editor)
        self.assertEqual(history.history_type, "edit")
        self.assertEqual(history.title, "曲のURLとカテゴリと模倣を編集")
        self.assertEqual(history.changes, [
            ["種類", "編集前", "編集後"],
            ["URL", "https://youtu.be/AAAAAAAAAAC,https://youtu.be/AAAAAAAAAAB",
             "https://youtu.be/AAAAAAAAAAC,https://youtu.be/AAAAAAAAAAB,https://youtu.be/AAAAAAAAAAA"],
            ["カテゴリ", "曲", "カバー"],
            ["模倣", "AAA\nCCC", "AAA\nBBB\nCCC"],
        ])

    def test_unchanged_song_has_no_history(self):
        create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        result = import_timeline([make_row()])

        self.assertEqual(result.unchanged, 1)
        self.assertEqual(result.updated, [])
        self.assertFalse(History.objects.exists())

    def test_second_run_changes_nothing(self):
        create_song("原曲")
        rows = [
            make_row(title="曲1", motif1="原曲枠", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(title="曲2", category="アレンジ", urls=["https://youtu.be/bbbbbbbbbbb", "https://nicovideo.jp/watch/sm1"]),
        ]
        import_timeline(rows)
        song_count = Song.objects.count()
        history_count = History.objects.count()

        result = import_timeline(rows)

        self.assertEqual((result.created, result.updated, result.unchanged), ([], [], 2))
        self.assertEqual(Song.objects.count(), song_count)
        self.assertEqual(History.objects.count(), history_count)

    def test_matches_url_with_different_format(self):
        # DBには「www.」付き・http・大文字小文字の違うURLが登録されていることがある
        song = create_song("曲", urls=["http://www.nicovideo.jp/watch/SM1", "https://x.com/SubeKashi/status/1"])
        result = import_timeline([make_row(urls=["https://nicovideo.jp/watch/sm1", "https://x.com/subekashi/status/1"])])

        self.assertEqual(result.unchanged, 1)
        self.assertEqual(song_urls(song), ["http://www.nicovideo.jp/watch/SM1", "https://x.com/SubeKashi/status/1"])

    def test_matches_nicovideo_url_for_smartphone_and_query(self):
        # スマホ版（sp.nicovideo.jp）や「?ref=」の付いたニコニコ動画のURLも、同じ動画のURLとして照合する
        song = create_song("曲", urls=["https://nicovideo.jp/watch/sm1"])
        result = import_timeline([
            make_row(urls=["https://sp.nicovideo.jp/watch/sm1?ref=user_video"]),
            make_row(urls=["https://nicovideo.jp/watch/sm1?ref=nicoiphone_other"]),
        ])

        self.assertEqual((result.created, result.unchanged), ([], 2))
        self.assertEqual(song_urls(song), ["https://nicovideo.jp/watch/sm1"])

    def test_youtube_id_is_case_sensitive(self):
        # YouTubeの動画IDは大文字小文字を区別するため、大文字小文字のみ違う動画は別の曲にする
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        result = import_timeline([make_row(title="別の曲", urls=["https://youtu.be/AAAAAAAAAAA"])])

        self.assertEqual([created.title for created in result.created], ["別の曲"])
        self.assertEqual(song_urls(song), ["https://youtu.be/aaaaaaaaaaa"])

    def test_bilibili_url_matches_av_and_bv(self):
        # ビリビリ動画のURLはclean_urlでBV番号のURLに揃えるため、av番号や「www.」・クエリの違うURLも同じ動画として照合する（#1246）
        song = create_song("曲", urls=["https://bilibili.com/video/BV1qV411J7Kq"])
        result = import_timeline([
            make_row(urls=["https://www.bilibili.com/video/av417727107/"]),
            make_row(urls=["https://www.bilibili.com/video/BV1qV411J7Kq/?spm_id_from=333.1387"]),
        ])

        self.assertEqual((result.created, result.unchanged), ([], 2))
        self.assertEqual(song_urls(song), ["https://bilibili.com/video/BV1qV411J7Kq"])

    def test_bilibili_id_is_case_sensitive(self):
        # BV番号は大文字小文字を区別するため、大文字小文字のみ違う動画は別の曲にする
        create_song("曲", urls=["https://bilibili.com/video/BV1qV411J7Kq"])
        result = import_timeline([make_row(title="別の曲", urls=["https://bilibili.com/video/BV1QV411J7KQ"])])

        self.assertEqual([created.title for created in result.created], ["別の曲"])

    def test_does_not_send_to_external_services(self):
        # --dry-runではDBの変更はロールバックされるが、外部への送信は取り消せないため、取り込みでは送信しない
        create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        with patch("subekashi.lib.discord.requests.post") as mock_post, patch("subekashi.lib.url.send_discord") as mock_send_discord:
            import_timeline([
                make_row(category="アレンジ", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"]),
                make_row(title="新しい曲", urls=["https://youtu.be/ccccccccccc"]),
            ])

        mock_post.assert_not_called()
        mock_send_discord.assert_not_called()

    def test_shared_url_does_not_identify_song(self):
        # 複数の曲で共有しているURL（allow_dup=True）は、紐づいている曲が1曲でもその曲の行とは決めない
        shared = SongLink.objects.create(url="https://youtu.be/sssssssssss", allow_dup=True)
        medley = create_song("メドレー")
        shared.songs.add(medley)
        result = import_timeline([make_row(title="新しい曲", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/sssssssssss"])])

        song = result.created[0]
        self.assertEqual(song_urls(song), ["https://youtu.be/sssssssssss", "https://youtu.be/aaaaaaaaaaa"])
        self.assertEqual(set(shared.songs.all()), {medley, song})
        medley.refresh_from_db()
        self.assertEqual(medley.category, "song")

    def test_shared_url_linked_to_multiple_songs_is_ignored(self):
        shared = SongLink.objects.create(url="https://youtu.be/sssssssssss", allow_dup=True)
        shared.songs.add(create_song("曲A"), create_song("曲B"))
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        import_timeline([make_row(category="アレンジ", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/sssssssssss"])])

        song.refresh_from_db()
        self.assertEqual(song.category, "arrange")
        self.assertIn("https://youtu.be/sssssssssss", song_urls(song))

    def test_skips_row_with_only_shared_url(self):
        # 共有しているURLしか無い行は、次の実行でもURLで照合できず毎日新規作成されてしまうため登録しない
        shared = SongLink.objects.create(url="https://youtu.be/sssssssssss", allow_dup=True)
        shared.songs.add(create_song("メドレー"))
        result = import_timeline([make_row(title="新しい曲", urls=["https://youtu.be/sssssssssss"])])

        self.assertEqual([reason for _, reason in result.skipped], ["複数の曲で共有しているURLのみ"])
        self.assertFalse(Song.objects.filter(title="新しい曲").exists())

    def test_skips_url_linked_to_multiple_songs(self):
        song1 = create_song("曲1", urls=["https://youtu.be/aaaaaaaaaaa"])
        create_song("曲2", urls=["https://youtu.be/bbbbbbbbbbb"])
        result = import_timeline([make_row(category="アレンジ", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])])

        self.assertEqual([reason for _, reason in result.skipped], ["複数の曲に一致"])
        song1.refresh_from_db()
        self.assertEqual(song1.category, "song")

    def test_updates_locked_song(self):
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"], is_lock=True)
        import_timeline([make_row(category="アレンジ", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])])

        song.refresh_from_db()
        self.assertEqual(song.category, "arrange")
        self.assertEqual(song_urls(song), ["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])

    def test_does_not_add_imitates_to_questionable_song(self):
        # 界隈曲?の曲は、編集画面と同様に模倣を登録しない
        create_song("原曲")
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"], is_questionable=True)
        import_timeline([make_row(motif1="原曲枠")])

        self.assertFalse(song.imitates.exists())

    def test_does_not_add_url_of_deleted_song_to_existing_song(self):
        SongLink.objects.create(url="https://youtu.be/bbbbbbbbbbb", is_removed=True)
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        import_timeline([make_row(urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])])

        self.assertEqual(song_urls(song), ["https://youtu.be/aaaaaaaaaaa"])

    def test_motif2_prefers_subeana_song(self):
        # 同じタイトルのアレンジなども登録されているため、モチーフ2も同じタイトルの曲が複数あればすべあなの曲にする
        subeana = create_song("エヌ", "全てあなたの所為です。")
        create_song("エヌ", "別の作者")
        result = import_timeline([make_row(motif2="→エヌ👤")])

        self.assertEqual(list(result.created[0].imitates.all()), [subeana])

    def test_motif2_with_same_title_songs_without_subeana_is_not_added(self):
        create_song(".", "別の作者A")
        create_song(".", "別の作者B")
        result = import_timeline([make_row(motif2="→.👤")])

        self.assertFalse(result.created[0].imitates.exists())

    def test_motif2_with_multiple_badges(self):
        # 合作の曲は「→生合成🔢😥」のように作者のバッジが複数付く
        collaboration = create_song("生合成", "全て十五の所為です。")
        result = import_timeline([
            make_row(motif2="→生合成🔢😥", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(motif2="→生合成🔢+", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ])

        self.assertEqual([list(song.imitates.all()) for song in result.created], [[collaboration], [collaboration]])

    def test_motif1_prefers_subeana_song(self):
        # モチーフ1（模倣の枠）はすべあなの曲のため、同じタイトルの曲が複数あってもすべあなの曲にする
        subeana = create_song(".", "全てあなたの所為です。")
        create_song(".", "別の作者")
        result = import_timeline([make_row(motif1=".枠")])

        self.assertEqual(list(result.created[0].imitates.all()), [subeana])

    def test_motif1_prefers_subeana_song_created_in_same_run(self):
        create_song("原曲", "別の作者")
        result = import_timeline([
            make_row(title="原曲", author="全てあなたの所為です。", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(title="模倣曲", motif1="原曲枠", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ])

        self.assertEqual(list(result.created[1].imitates.all()), [result.created[0]])

    def test_motif1_without_subeana_song(self):
        # すべあなの曲が無ければ、モチーフ2と同様にタイトルが一致する曲が1曲のときのみ追加する
        other = create_song("無題です。", "別の作者")
        create_song("..", "別の作者A")
        create_song("..", "別の作者B")
        result = import_timeline([
            make_row(motif1="無題です。枠", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(motif1="..枠", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ])

        self.assertEqual(list(result.created[0].imitates.all()), [other])
        self.assertFalse(result.created[1].imitates.exists())

    def test_motif_titles_alias(self):
        hyouri = create_song("表/裏", "全てあなたの所為です。")
        create_song("表裏", "別の作者")
        star = create_song("名の無い星が空に堕ちたら", "全てあなたの所為です。")
        result = import_timeline([make_row(motif1="表裏枠", motif2="名の無い星")])

        self.assertEqual(set(result.created[0].imitates.all()), {hyouri, star})

    def test_motif2_prefers_unstripped_title(self):
        # 記号で終わるタイトルの曲は、記号を削らずに探す
        symbol = create_song("❁", "別の作者")
        star = create_song("曲★", "別の作者")
        create_song("曲", "別の作者")
        mohou = create_song("全てが適当すぎた.模倣", "別の作者")
        result = import_timeline([
            make_row(motif2="→❁", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(motif2="→曲★", urls=["https://youtu.be/bbbbbbbbbbb"]),
            make_row(motif2="全てが適当すぎた.模倣", urls=["https://youtu.be/ccccccccccc"]),
        ])

        self.assertEqual([list(song.imitates.all()) for song in result.created], [[symbol], [star], [mohou]])

    def test_motif_does_not_add_self(self):
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        import_timeline([make_row(motif2="→曲👤")])

        self.assertFalse(song.imitates.exists())

    def test_motif_can_be_song_created_in_same_run(self):
        result = import_timeline([
            make_row(title="原曲", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(title="模倣曲", motif1="原曲枠", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ])

        self.assertEqual(list(result.created[1].imitates.all()), [result.created[0]])

    def test_rows_sharing_url_update_created_song(self):
        result = import_timeline([
            make_row(title="先行公開", category="音mad", urls=["https://soundcloud.com/user/song"]),
            make_row(title="本公開", category="曲", urls=["https://nicovideo.jp/watch/sm1", "https://soundcloud.com/user/song"]),
        ])

        song = result.created[0]
        self.assertEqual(len(result.created), 1)
        self.assertEqual(song_urls(song), ["https://soundcloud.com/user/song", "https://nicovideo.jp/watch/sm1"])
        # 複数の行に一致する曲は、カテゴリが毎回行ごとに入れ替わらないよう最初の行のカテゴリにする
        song.refresh_from_db()
        self.assertEqual(song.category, "otomad")

    def test_empty_category_does_not_change_category(self):
        # カテゴリが空欄の行は、サイトで設定されたカテゴリを変えない（新規作成では曲にする）
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"], category="arrange")
        result = import_timeline([make_row(category="")])

        song.refresh_from_db()
        self.assertEqual(song.category, "arrange")
        self.assertEqual(result.unchanged, 1)

    def test_category_row_after_empty_category_row(self):
        # カテゴリが空欄の行はカテゴリを決めないため、後の行のカテゴリにする
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])
        import_timeline([
            make_row(category="", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(category="カバー", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ])

        song.refresh_from_db()
        self.assertEqual(song.category, "cover")

    def test_category_of_song_matched_by_rows_does_not_flip(self):
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])
        rows = [
            make_row(category="アレンジ", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(category="カバー", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ]
        import_timeline(rows)
        import_timeline(rows)

        song.refresh_from_db()
        self.assertEqual(song.category, "arrange")
        self.assertEqual(song.histories.count(), 1)

    def test_updates_lyrics_song_with_same_title_or_author(self):
        same_title = create_song("曲", "サイトの作者")
        same_author = create_song("サイトのタイトル", "作者")
        result = import_timeline([
            make_row(urls=["https://youtu.be/aaaaaaaaaaa"], lyrics_url=f"https://lyrics.imicomweb.com/songs/{same_title.id}"),
            make_row(urls=["https://youtu.be/bbbbbbbbbbb"], lyrics_url=f"https://lyrics.imicomweb.com/songs/{same_author.id}/"),
        ])

        self.assertEqual(result.created, [])
        self.assertEqual(song_urls(same_title), ["https://youtu.be/aaaaaaaaaaa"])
        self.assertEqual(song_urls(same_author), ["https://youtu.be/bbbbbbbbbbb"])

    def test_skips_lyrics_song_with_only_author_and_different_version(self):
        # full版の行の歌詞列がshort版の曲を指していることがあるため、作者だけが一致する場合はshort版かどうかも同じ曲に限る
        short = create_song("曲[short]", "作者")
        result = import_timeline([make_row(title="曲", lyrics_url=f"https://lyrics.imicomweb.com/songs/{short.id}")])

        self.assertEqual([reason for _, reason in result.skipped], ["歌詞列の曲とshort版かどうかが異なる"])
        self.assertEqual(song_urls(short), [])

    def test_updates_lyrics_song_with_only_author_and_same_version(self):
        short = create_song("曲[Short]", "作者")
        import_timeline([make_row(title="曲[short]", lyrics_url=f"https://lyrics.imicomweb.com/songs/{short.id}")])

        self.assertEqual(song_urls(short), ["https://youtu.be/aaaaaaaaaaa"])

    def test_skips_lyrics_song_with_different_title_and_author(self):
        song = create_song("別の曲", "別の作者")
        result = import_timeline([make_row(lyrics_url=f"https://lyrics.imicomweb.com/songs/{song.id}")])

        self.assertEqual([reason for _, reason in result.skipped], ["歌詞列の曲とタイトル・作者が一致しない"])
        self.assertEqual(Song.objects.count(), 1)

    def test_lyrics_song_not_found_creates_song(self):
        result = import_timeline([make_row(lyrics_url="https://lyrics.imicomweb.com/songs/999999")])

        self.assertEqual(len(result.created), 1)

    def test_url_match_takes_priority_over_lyrics(self):
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        other = create_song("曲", "作者")
        import_timeline([make_row(category="アレンジ", lyrics_url=f"https://lyrics.imicomweb.com/songs/{other.id}")])

        song.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(song.category, "arrange")
        self.assertEqual(other.category, "song")

    def test_creates_song_with_prush(self):
        # プ列のプレラを曲に登録する（#1064）
        result = import_timeline([make_row(premiere_rush="年末プレラ５")])

        song = result.created[0]
        self.assertEqual(song.prush.name, "年末プレラ５")
        self.assertIn(["プレラ", "年末プレラ５"], song.histories.get().changes)

    def test_rows_share_prush(self):
        result = import_timeline([
            make_row(title="曲1", premiere_rush="年末プレラ５", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(title="曲2", premiere_rush="年末プレラ５", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ])

        self.assertEqual(result.created[0].prush, result.created[1].prush)
        self.assertEqual(Prush.objects.count(), 1)

    def test_prush_matches_full_and_half_width(self):
        # 年末のプレラが翌年まで続くと、全角・半角が違うことがある（「年末プレラ３」と「年末プレラ3」）
        prush = Prush.objects.create(name="年末プレラ３")
        result = import_timeline([make_row(premiere_rush="年末プレラ3")])

        self.assertEqual(result.created[0].prush, prush)
        self.assertEqual(Prush.objects.count(), 1)

    def test_updates_prush(self):
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"])
        import_timeline([make_row(premiere_rush="年末プレラ５")])

        song.refresh_from_db()
        self.assertEqual(song.prush.name, "年末プレラ５")
        history = song.histories.get()
        self.assertEqual(history.title, "曲のプレラを編集")
        self.assertEqual(history.changes, [["種類", "編集前", "編集後"], ["プレラ", "", "年末プレラ５"]])

    def test_changes_prush(self):
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"], prush=Prush.objects.create(name="夏プレラ"))
        import_timeline([make_row(premiere_rush="晩夏プレラ6")])

        song.refresh_from_db()
        self.assertEqual(song.prush.name, "晩夏プレラ6")
        self.assertIn(["プレラ", "夏プレラ", "晩夏プレラ6"], song.histories.get().changes)

    def test_empty_prush_does_not_clear_prush(self):
        # プ列が空欄の行は、登録されているプレラを消さない
        prush = Prush.objects.create(name="夏プレラ")
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa"], prush=prush)
        result = import_timeline([make_row()])

        song.refresh_from_db()
        self.assertEqual(song.prush, prush)
        self.assertEqual(result.unchanged, 1)

    def test_prush_of_first_row_is_used(self):
        # 複数の行に一致する曲は、プレラが毎回入れ替わらないよう最初の行のプレラにする
        song = create_song("曲", urls=["https://youtu.be/aaaaaaaaaaa", "https://youtu.be/bbbbbbbbbbb"])
        rows = [
            make_row(premiere_rush="夏プレラ", urls=["https://youtu.be/aaaaaaaaaaa"]),
            make_row(premiere_rush="晩夏プレラ6", urls=["https://youtu.be/bbbbbbbbbbb"]),
        ]
        import_timeline(rows)
        import_timeline(rows)

        song.refresh_from_db()
        self.assertEqual(song.prush.name, "夏プレラ")
        self.assertEqual(song.histories.count(), 1)
        self.assertFalse(Prush.objects.filter(name="晩夏プレラ6").exists())

    def test_skipped_row_does_not_create_prush(self):
        result = import_timeline([make_row(author="掲載拒否の作者", premiere_rush="夏プレラ")])

        self.assertEqual([reason for _, reason in result.skipped], ["掲載拒否の作者"])
        self.assertFalse(Prush.objects.exists())

    def test_recreates_deleted_editor(self):
        self.editor.delete()
        import_timeline([make_row()])

        history = History.objects.get()
        self.assertEqual(history.editor_id, 1)
