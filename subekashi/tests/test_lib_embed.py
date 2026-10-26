"""
lib/embed.py のテスト

曲ページの埋め込みプレイヤー（#1254）のため、URLから埋め込み用のURLとiframeの形を求める関数を検証する。
"""
from django.test import SimpleTestCase
from subekashi.lib.embed import get_embed


class GetEmbedYoutubeTest(SimpleTestCase):
    """YouTube"""

    def test_short_url(self):
        self.assertEqual(
            get_embed("https://youtu.be/dQw4w9WgXcQ"),
            {"src": "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "shape": "video"},
        )

    def test_watch_url(self):
        self.assertEqual(
            get_embed("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30")["src"],
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_shorts_url(self):
        self.assertEqual(
            get_embed("https://youtube.com/shorts/dQw4w9WgXcQ")["src"],
            "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ",
        )

    def test_youtube_url_in_other_site_query_is_not_embedded(self):
        self.assertIsNone(get_embed("https://x.com/user/status/1?u=https://youtu.be/dQw4w9WgXcQ"))

    def test_channel_page_is_not_embedded(self):
        self.assertIsNone(get_embed("https://www.youtube.com/@subekashi"))


class GetEmbedNicovideoTest(SimpleTestCase):
    """ニコニコ動画"""

    def test_watch_url(self):
        self.assertEqual(
            get_embed("https://nicovideo.jp/watch/sm12345678"),
            {"src": "https://embed.nicovideo.jp/watch/sm12345678", "shape": "video"},
        )

    def test_id_prefixes(self):
        for video_id in ["sm1", "nm1", "so1", "1234567890"]:
            with self.subTest(video_id=video_id):
                self.assertEqual(get_embed(f"https://nicovideo.jp/watch/{video_id}")["src"], f"https://embed.nicovideo.jp/watch/{video_id}")

    def test_query_is_removed(self):
        self.assertEqual(get_embed("https://nicovideo.jp/watch/sm12345678?ref=twitter&from=30")["src"], "https://embed.nicovideo.jp/watch/sm12345678")

    def test_www_and_smartphone_host(self):
        self.assertEqual(get_embed("https://www.nicovideo.jp/watch/sm1")["src"], "https://embed.nicovideo.jp/watch/sm1")
        self.assertEqual(get_embed("https://sp.nicovideo.jp/watch/sm1")["src"], "https://embed.nicovideo.jp/watch/sm1")

    def test_non_video_pages_are_not_embedded(self):
        for url in ["https://nicovideo.jp/user/12345", "https://nicovideo.jp/mylist/12345", "https://nicovideo.jp/watch/", "https://nicovideo.jp/watch/sm12345abc"]:
            with self.subTest(url=url):
                self.assertIsNone(get_embed(url))


class GetEmbedSoundcloudTest(SimpleTestCase):
    """SoundCloud"""

    def test_track_url(self):
        self.assertEqual(
            get_embed("https://soundcloud.com/artist/track-name"),
            {"src": "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Ftrack-name&visual=false", "shape": "audio"},
        )

    def test_playlist_url(self):
        self.assertEqual(
            get_embed("https://soundcloud.com/artist/sets/album-name"),
            {"src": "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Fsets%2Falbum-name&visual=false", "shape": "playlist"},
        )

    def test_query_and_trailing_slash_are_removed(self):
        self.assertEqual(
            get_embed("https://soundcloud.com/artist/track-name/?si=abc&utm_source=clipboard")["src"],
            "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Ftrack-name&visual=false",
        )

    def test_mobile_host(self):
        self.assertEqual(
            get_embed("https://m.soundcloud.com/artist/track-name")["src"],
            "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Ftrack-name&visual=false",
        )

    def test_percent_encoded_path_is_encoded_once_more(self):
        self.assertEqual(
            get_embed("https://soundcloud.com/artist/%E6%9B%B2")["src"],
            "https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2F%25E6%259B%25B2&visual=false",
        )

    def test_user_page_and_tabs_are_not_embedded(self):
        for url in [
            "https://soundcloud.com/artist",
            "https://soundcloud.com/artist/tracks",
            "https://soundcloud.com/artist/sets",
            "https://soundcloud.com/artist/likes",
            "https://soundcloud.com/artist/track-name/recommended",
            "https://soundcloud.com/",
        ]:
            with self.subTest(url=url):
                self.assertIsNone(get_embed(url))

    def test_short_link_is_not_embedded(self):
        # 「on.soundcloud.com/xxx」の短縮URLは、プレイヤーが「有効なSoundCloudのURLではない」と表示するため対象外
        self.assertIsNone(get_embed("https://on.soundcloud.com/d3pgp"))

    def test_other_host_is_not_embedded(self):
        self.assertIsNone(get_embed("https://example.com/artist/track-name"))


class GetEmbedBilibiliTest(SimpleTestCase):
    """ビリビリ動画"""

    def test_bv_url(self):
        self.assertEqual(
            get_embed("https://bilibili.com/video/BV1qV411J7Kq"),
            {"src": "https://player.bilibili.com/player.html?isOutside=true&bvid=BV1qV411J7Kq&p=1&autoplay=0", "shape": "video"},
        )

    def test_part_number(self):
        self.assertEqual(
            get_embed("https://bilibili.com/video/BV1qV411J7Kq?p=3")["src"],
            "https://player.bilibili.com/player.html?isOutside=true&bvid=BV1qV411J7Kq&p=3&autoplay=0",
        )

    def test_www_host_and_extra_query(self):
        self.assertEqual(
            get_embed("https://www.bilibili.com/video/BV1qV411J7Kq/?spm_id_from=333&p=2")["src"],
            "https://player.bilibili.com/player.html?isOutside=true&bvid=BV1qV411J7Kq&p=2&autoplay=0",
        )

    def test_av_url_is_converted_to_bv(self):
        self.assertEqual(
            get_embed("https://bilibili.com/video/av170001")["src"],
            "https://player.bilibili.com/player.html?isOutside=true&bvid=BV17x411w7KC&p=1&autoplay=0",
        )

    def test_non_video_page_is_not_embedded(self):
        self.assertIsNone(get_embed("https://bilibili.com/read/cv123"))
        self.assertIsNone(get_embed("https://space.bilibili.com/123"))


class GetEmbedGoogleDriveTest(SimpleTestCase):
    """Google Drive"""

    def test_file_url(self):
        self.assertEqual(
            get_embed("https://drive.google.com/file/d/1aB-cD_eF2gH/view?usp=sharing"),
            {"src": "https://drive.google.com/file/d/1aB-cD_eF2gH/preview", "shape": "video"},
        )

    def test_file_url_with_account_index(self):
        self.assertEqual(
            get_embed("https://drive.google.com/file/u/0/d/1aB-cD_eF2gH/view")["src"],
            "https://drive.google.com/file/d/1aB-cD_eF2gH/preview",
        )

    def test_folder_url_is_not_embedded(self):
        self.assertIsNone(get_embed("https://drive.google.com/drive/folders/1aB-cD_eF2gH"))


class GetEmbedScratchTest(SimpleTestCase):
    """Scratch"""

    def test_project_url(self):
        self.assertEqual(
            get_embed("https://scratch.mit.edu/projects/123456789"),
            {"src": "https://scratch.mit.edu/projects/123456789/embed", "shape": "scratch"},
        )

    def test_project_editor_url(self):
        self.assertEqual(get_embed("https://scratch.mit.edu/projects/123456789/editor")["src"], "https://scratch.mit.edu/projects/123456789/embed")

    def test_user_and_studio_page_are_not_embedded(self):
        self.assertIsNone(get_embed("https://scratch.mit.edu/users/someone"))
        self.assertIsNone(get_embed("https://scratch.mit.edu/studios/123"))


class GetEmbedUnsupportedTest(SimpleTestCase):
    """埋め込みに対応していないURL"""

    def test_services_without_official_iframe(self):
        for url in [
            "https://x.com/user/status/1234567890",
            "https://bandcamp.com/album/name",
            "https://bsky.app/profile/user.bsky.social/post/abc",
            "https://piapro.jp/t/abcd",
            "https://booth.pm/ja/items/123",
        ]:
            with self.subTest(url=url):
                self.assertIsNone(get_embed(url))

    def test_empty_and_plain_text(self):
        self.assertIsNone(get_embed(""))
        self.assertIsNone(get_embed("not a url"))

    def test_javascript_scheme_is_not_embedded(self):
        self.assertIsNone(get_embed("javascript:alert(1)//youtu.be/dQw4w9WgXcQ"))
