"""
ogp テンプレートタグのテスト（#1058）

get_ogp_image_url(): metatitleを署名したトークンでog:imageのURLを作る。
metatitleが無い・空白のみの場合は共通の画像（ogp.png）のURLを返す。
"""
import re
from django.conf import settings
from django.test import SimpleTestCase, override_settings
from subekashi.lib.ogp import OGP_VERSION, load_ogp_token
from subekashi.templatetags.ogp import get_ogp_image_url


STATIC_STORAGE = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=STATIC_STORAGE)
class GetOgpImageUrlTest(SimpleTestCase):
    """get_ogp_image_url() のテスト"""

    def _get_title(self, url):
        match = re.fullmatch(rf"{re.escape(settings.ROOT_URL)}/ogp/([^/]+)\.png\?v={OGP_VERSION}", url)
        self.assertIsNotNone(match)
        return load_ogp_token(match.group(1))

    def test_metatitle_makes_ogp_image_url_with_version(self):
        self.assertEqual(self._get_title(get_ogp_image_url("トップ")), "トップ")

    def test_metatitle_is_normalized(self):
        self.assertEqual(self._get_title(get_ogp_image_url("  トップ　")), "トップ")
        self.assertEqual(self._get_title(get_ogp_image_url("曲名\n­作者")), "曲名 作者")

    def test_empty_metatitle_returns_static_image_url(self):
        static_url = f"{settings.ROOT_URL}/static/subekashi/image/ogp.png"
        for metatitle in [None, "", " ", "　\n", "­ ​"]:
            with self.subTest(metatitle=metatitle):
                self.assertEqual(get_ogp_image_url(metatitle), static_url)

    @override_settings(ROOT_URL="https://example.com")
    def test_uses_root_url_setting(self):
        self.assertTrue(get_ogp_image_url("トップ").startswith("https://example.com/ogp/"))
        self.assertEqual(get_ogp_image_url(""), "https://example.com/static/subekashi/image/ogp.png")
