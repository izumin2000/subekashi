"""
lib/url.py のテスト

URL正規化・判定・メディア情報取得のユーティリティ関数を対象とする。
外部通信は SEND_DISCORD=False のため実際には送信されない。
"""
from django.test import SimpleTestCase
from subekashi.lib.url import (
    is_youtube_url,
    get_youtube_id,
    format_youtube_url,
    format_x_url,
    convert_av_to_bv,
    format_bilibili_url,
    clean_url,
    get_allow_media,
    get_all_media,
)


class IsYoutubeUrlTest(SimpleTestCase):
    """is_youtube_url() のテスト"""

    def test_standard_youtube_url(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_youtube_url_without_www(self):
        self.assertTrue(is_youtube_url("https://youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_mobile_youtube_url(self):
        self.assertTrue(is_youtube_url("https://m.youtube.com/watch?v=dQw4w9WgXcQ"))

    def test_youtu_be_short_url(self):
        self.assertTrue(is_youtube_url("https://youtu.be/dQw4w9WgXcQ"))

    def test_youtube_shorts_url(self):
        self.assertTrue(is_youtube_url("https://youtube.com/shorts/abcdefghijk"))

    def test_youtube_url_with_extra_params(self):
        self.assertTrue(is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30"))

    def test_niconico_url_is_not_youtube(self):
        self.assertFalse(is_youtube_url("https://nicovideo.jp/watch/sm12345678"))

    def test_x_url_is_not_youtube(self):
        self.assertFalse(is_youtube_url("https://x.com/user/status/123"))

    def test_empty_string(self):
        self.assertFalse(is_youtube_url(""))

    def test_plain_text(self):
        self.assertFalse(is_youtube_url("youtube"))


class GetYoutubeIdTest(SimpleTestCase):
    """get_youtube_id() のテスト"""

    def test_standard_url(self):
        self.assertEqual(
            get_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_youtu_be_url(self):
        self.assertEqual(
            get_youtube_id("https://youtu.be/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_shorts_url(self):
        self.assertEqual(
            get_youtube_id("https://youtube.com/shorts/abcdefghijk"),
            "abcdefghijk",
        )

    def test_non_youtube_url_returns_original(self):
        url = "https://example.com"
        self.assertEqual(get_youtube_id(url), url)


class FormatYoutubeUrlTest(SimpleTestCase):
    """format_youtube_url() のテスト"""

    def test_standard_url_is_shortened(self):
        self.assertEqual(
            format_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "https://youtu.be/dQw4w9WgXcQ",
        )

    def test_already_short_url_is_unchanged(self):
        self.assertEqual(
            format_youtube_url("https://youtu.be/dQw4w9WgXcQ"),
            "https://youtu.be/dQw4w9WgXcQ",
        )

    def test_non_youtube_url_is_unchanged(self):
        url = "https://nicovideo.jp/watch/sm12345678"
        self.assertEqual(format_youtube_url(url), url)

    def test_youtube_url_with_timestamp(self):
        self.assertEqual(
            format_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30"),
            "https://youtu.be/dQw4w9WgXcQ",
        )


class FormatXUrlTest(SimpleTestCase):
    """format_x_url() のテスト"""

    def test_twitter_url_query_is_removed(self):
        self.assertEqual(
            format_x_url("https://twitter.com/user/status/123?s=20"),
            "https://x.com/user/status/123",
        )

    def test_x_com_url_unchanged(self):
        self.assertEqual(
            format_x_url("https://x.com/user/status/123"),
            "https://x.com/user/status/123",
        )

    def test_twitter_scheme_normalized_to_https(self):
        result = format_x_url("http://twitter.com/user/status/123")
        self.assertTrue(result.startswith("https://"))

    def test_twitter_domain_normalized_to_x_com(self):
        result = format_x_url("https://twitter.com/user/status/123")
        self.assertIn("x.com", result)

    def test_non_x_url_is_unchanged(self):
        url = "https://example.com/path?q=1"
        self.assertEqual(format_x_url(url), url)

    def test_fragment_is_removed(self):
        result = format_x_url("https://twitter.com/user/status/123#top")
        self.assertNotIn("#top", result)


class ConvertAvToBvTest(SimpleTestCase):
    """convert_av_to_bv() のテスト（#1246）"""

    def test_known_pairs(self):
        cases = [
            # ビリビリ動画がBV番号を導入したときに例として示した組
            (170001, "BV17x411w7KC"),
            # すべあな界隈年表にBV番号で、DBにav番号で登録されていた動画
            (417727107, "BV1qV411J7Kq"),
            # av番号が2^30を超えた2024年以降の動画
            (111298867365120, "BV1L9Uoa9EUx"),
        ]
        for aid, bvid in cases:
            with self.subTest(aid=aid):
                self.assertEqual(convert_av_to_bv(aid), bvid)


class FormatBilibiliUrlTest(SimpleTestCase):
    """format_bilibili_url() のテスト（#1246）"""

    def test_www_trailing_slash_and_query_are_removed(self):
        self.assertEqual(
            format_bilibili_url("https://www.bilibili.com/video/BV11ar4YcEyF/?spm_id_from=333.1387.homepage.video_card.click&vd_source=e58d08ec4f151c8816a037087220fbd5"),
            "https://bilibili.com/video/BV11ar4YcEyF",
        )

    def test_formatted_url_is_unchanged(self):
        url = "https://bilibili.com/video/BV11ar4YcEyF"
        self.assertEqual(format_bilibili_url(url), url)

    def test_mobile_and_http_url_are_formatted(self):
        for url in ["https://m.bilibili.com/video/BV11ar4YcEyF", "http://bilibili.com/video/BV11ar4YcEyF#reply"]:
            with self.subTest(url=url):
                self.assertEqual(format_bilibili_url(url), "https://bilibili.com/video/BV11ar4YcEyF")

    def test_av_url_is_converted_to_bv(self):
        self.assertEqual(
            format_bilibili_url("https://www.bilibili.com/video/av417727107/"),
            "https://bilibili.com/video/BV1qV411J7Kq",
        )

    def test_page_after_first_is_kept(self):
        # すべあな界隈年表には、1つの動画のパートごとに別の曲が載っている
        cases = [
            ("https://www.bilibili.com/video/BV1in4y1Q7qw?p=1", "https://bilibili.com/video/BV1in4y1Q7qw"),
            ("https://www.bilibili.com/video/BV1in4y1Q7qw?p=2", "https://bilibili.com/video/BV1in4y1Q7qw?p=2"),
            ("https://www.bilibili.com/video/BV1in4y1Q7qw?p=3&vd_source=e746505daf0168401b3bf90bae76310d", "https://bilibili.com/video/BV1in4y1Q7qw?p=3"),
            ("https://bilibili.com/video/av417727107/?spm_id_from=333.999.0.0&p=02", "https://bilibili.com/video/BV1qV411J7Kq?p=2"),
            ("https://bilibili.com/video/BV1in4y1Q7qw?p=abc", "https://bilibili.com/video/BV1in4y1Q7qw"),
        ]
        for url, expected in cases:
            with self.subTest(url=url):
                self.assertEqual(format_bilibili_url(url), expected)

    def test_url_without_video_id_is_unchanged(self):
        for url in [
            # BV番号の桁数が多い（すべあな界隈年表にある誤記）
            "https://www.bilibili.com/video/BV1bcvtezEAcc",
            # BV番号に変換できない大きさのav番号
            "https://www.bilibili.com/video/av2251799813685248",
            "https://www.bilibili.com/audio/au2080348",
            "https://space.bilibili.com/12345678",
            "https://bilibili.com.attacker.example/video/BV11ar4YcEyF",
            "https://nicovideo.jp/watch/sm12345678",
        ]:
            with self.subTest(url=url):
                self.assertEqual(format_bilibili_url(url), url)


class CleanUrlTest(SimpleTestCase):
    """clean_url() のテスト"""

    def test_space_before_comma_is_removed(self):
        result = clean_url("https://youtu.be/aaaaaaaaaaa ,https://youtu.be/bbbbbbbbbbb")
        self.assertNotIn(" ", result)

    def test_space_after_comma_is_removed(self):
        result = clean_url("https://youtu.be/aaaaaaaaaaa, https://youtu.be/bbbbbbbbbbb")
        self.assertNotIn(" ,", result)
        self.assertNotIn(", ", result)

    def test_www_is_removed_from_url(self):
        result = clean_url("https://www.nicovideo.jp/watch/sm12345678")
        self.assertNotIn("//www.", result)

    def test_youtube_url_is_shortened(self):
        result = clean_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(result, "https://youtu.be/dQw4w9WgXcQ")

    def test_google_redirect_prefix_is_removed(self):
        result = clean_url("https://www.google.com/url?q=https://youtu.be/dQw4w9WgXcQ")
        self.assertNotIn("google.com", result)

    def test_multiple_urls_are_joined_with_comma(self):
        result = clean_url("https://youtu.be/aaaaaaaaaaa,https://youtu.be/bbbbbbbbbbb")
        parts = result.split(",")
        self.assertEqual(len(parts), 2)

    def test_twitter_url_is_normalized(self):
        result = clean_url("https://twitter.com/user/status/123?s=20")
        self.assertIn("x.com", result)
        self.assertNotIn("?s=20", result)

    def test_bilibili_url_is_formatted(self):
        result = clean_url("https://www.bilibili.com/video/av417727107/,https://www.bilibili.com/video/BV1in4y1Q7qw/?p=2")
        self.assertEqual(result, "https://bilibili.com/video/BV1qV411J7Kq,https://bilibili.com/video/BV1in4y1Q7qw?p=2")

    def test_trailing_slash_is_removed(self):
        result = clean_url("https://nicovideo.jp/watch/sm12345678/")
        self.assertFalse(result.endswith('/'))

    def test_trailing_slash_removed_from_multiple_urls(self):
        result = clean_url("https://nicovideo.jp/watch/sm12345678/,https://x.com/user/status/123/")
        for url in result.split(","):
            self.assertFalse(url.endswith('/'))


class GetAllowMediaTest(SimpleTestCase):
    """get_allow_media() のテスト"""

    def test_youtube_url_returns_youtube_media(self):
        result = get_allow_media("https://youtu.be/dQw4w9WgXcQ")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "youtube")

    def test_x_url_returns_x_media(self):
        result = get_allow_media("https://x.com/user/status/123")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "x")

    def test_nicovideo_url_returns_nicovideo_media(self):
        result = get_allow_media("https://nicovideo.jp/watch/sm12345678")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "nicovideo")

    def test_unknown_url_returns_false(self):
        result = get_allow_media("https://unknown-domain-xyz.example.com/path")
        self.assertFalse(result)

    def test_soundcloud_url_returns_soundcloud_media(self):
        result = get_allow_media("https://soundcloud.com/artist/track")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "soundcloud")

    def test_bluesky_url_returns_bluesky_media(self):
        result = get_allow_media("https://bsky.app/profile/example.bsky.social")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "bluesky")

    def test_vimesis_url_returns_vimesis_media(self):
        result = get_allow_media("https://main.vimesis.com/channel/@subekashi")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "vimesis")

    def test_vimesis_dot_not_treated_as_wildcard(self):
        # Issue #1056: 正規表現のドットが未エスケープだと "vimesisXcom" のような
        # 文字列にも誤マッチしてしまうため、エスケープ後は許可されないことを確認する
        result = get_allow_media("https://vimesisXcom.example.net/")
        self.assertFalse(result)

    def test_youtube_dot_not_treated_as_wildcard(self):
        result = get_allow_media("https://youtuXbe.example.net/")
        self.assertFalse(result)

    def test_x_dot_not_treated_as_wildcard(self):
        result = get_allow_media("https://xXcom.example.net/")
        self.assertFalse(result)

    def test_nicovideo_dot_not_treated_as_wildcard(self):
        result = get_allow_media("https://nicovideoXjp.example.net/")
        self.assertFalse(result)

    def test_soundcloud_dot_not_treated_as_wildcard(self):
        result = get_allow_media("https://soundcloudXcom.example.net/")
        self.assertFalse(result)

    def test_bandcamp_dot_not_treated_as_wildcard(self):
        result = get_allow_media("https://bandcampXcom.example.net/")
        self.assertFalse(result)

    def test_bilibili_dot_not_treated_as_wildcard(self):
        result = get_allow_media("https://bilibiliXcom.example.net/")
        self.assertFalse(result)

    def test_vimesis_domain_suffix_spoofing_returns_false(self):
        # 末尾側に境界チェックがないと vimesis.com.attacker.example のような
        # なりすましドメインにも誤マッチしてしまうため、拒否されることを確認する
        result = get_allow_media("https://vimesis.com.attacker.example/")
        self.assertFalse(result)

    def test_note_domain_prefix_spoofing_returns_false(self):
        # note のように元々先頭側の境界チェックがなかったエントリでも
        # xnote.comevil.net のような部分一致で誤マッチしないことを確認する
        result = get_allow_media("https://xnote.comevil.net/")
        self.assertFalse(result)

    def test_note_url_returns_note_media(self):
        result = get_allow_media("https://note.com/articles/abc123")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "note")

    def test_timeline_media_urls_return_media(self):
        # Issue #1247: すべあな界隈年表にあるURLは、曲の編集と同じくclean_urlを通してから判定しても許可される
        cases = [
            ("https://bowlroll.net/file/284458", "bowlroll"),
            ("https://misskey.io/notes/9t0cp2dmpjod01ls", "misskey"),
            ("https://booth.pm/ja/items/5057223", "booth"),
            ("https://example.booth.pm/items/5057223", "booth"),
            ("https://piapro.jp/t/WuJy", "piapro"),
            ("https://rechord.cc/4-DF3Y99flI", "rechord"),
            ("https://www.dropbox.com/scl/fi/abc/song.mp3?rlkey=xyz&dl=0", "dropbox"),
        ]
        for url, media_id in cases:
            with self.subTest(url=url):
                result = get_allow_media(clean_url(url))
                self.assertIsNot(result, False)
                self.assertEqual(result["id"], media_id)

    def test_timeline_media_spoofed_domains_return_false(self):
        for url in [
            "https://bowlrollXnet.example.net/",
            "https://xmisskey.io/",
            "https://booth.pm.attacker.example/",
            "https://piapro.jp.attacker.example/",
            "https://xrechord.cc/",
            "https://dropbox.com.attacker.example/",
        ]:
            with self.subTest(url=url):
                self.assertFalse(get_allow_media(url))

    def test_discord_url_returns_false(self):
        # Issue #1247: Discordのメッセージのリンクはサーバーの参加者しか見られないため許可しない
        result = get_allow_media("https://discord.com/channels/111/222/333")
        self.assertFalse(result)


class GetAllMediaTest(SimpleTestCase):
    """get_all_media() のテスト（SEND_DISCORD=False のため外部送信なし）"""

    def test_youtube_url_returns_youtube_media(self):
        result = get_all_media("https://youtu.be/dQw4w9WgXcQ")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "youtube")

    def test_x_url_returns_x_media(self):
        result = get_all_media("https://x.com/user/status/123")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "x")

    def test_nicovideo_url_returns_nicovideo_media(self):
        result = get_all_media("https://nicovideo.jp/watch/sm12345678")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "nicovideo")

    def test_booth_url_returns_booth_media(self):
        # Issue #1247: 許可したドメインは「許可されていないURL」として表示されない
        result = get_all_media("https://booth.pm/ja/items/5057223")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "booth")

    def test_unknown_url_returns_disallow_media(self):
        # 未登録URLは disallow エントリにフォールバックする（send_discordが呼ばれるがDEBUG=Trueのため送信なし）
        result = get_all_media("https://totally-unknown-domain-abc123.example.com/")
        self.assertIsNot(result, False)
        self.assertEqual(result["id"], "disallow")

    def test_result_contains_required_keys(self):
        result = get_all_media("https://youtu.be/dQw4w9WgXcQ")
        self.assertIn("id", result)
        self.assertIn("name", result)
        self.assertIn("icon", result)
