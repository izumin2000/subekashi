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


class CleanUrlTest(SimpleTestCase):
    """clean_url() のテスト"""

    def test_space_before_comma_is_removed(self):
        result = clean_url("https://youtu.be/aaaaaaaaaaа ,https://youtu.be/bbbbbbbbbbb")
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
