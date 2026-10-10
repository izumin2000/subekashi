"""
lib/ogp.py のテスト

ページごとのOGP画像（#1058）について、タイトルを署名したトークンの作成・検証、
タイトルの折り返し・フォントサイズの決定、画像の生成を検証する。
"""
import io
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from django.core import signing
from django.test import SimpleTestCase
from PIL import Image, ImageDraw
from subekashi.lib.ogp import (
    BACKGROUND_COLOR,
    OGP_TITLE_MAX_LENGTH,
    TITLE_FONT_SIZES,
    TITLE_MAX_HEIGHT,
    TITLE_MAX_LINES,
    TITLE_MAX_WIDTH,
    get_font,
    get_text_height,
    layout_title,
    load_ogp_token,
    make_ogp_token,
    normalize_title,
    render_ogp_image,
    wrap_text,
)


class NormalizeTitleTest(SimpleTestCase):
    """normalize_title() のテスト"""

    def test_collapses_whitespace_and_newlines(self):
        self.assertEqual(normalize_title(" 曲名\n\t作者  名　前 "), "曲名 作者 名 前")

    def test_removes_invisible_format_characters(self):
        # ソフトハイフン・ゼロ幅スペース・ゼロ幅非接合子
        self.assertEqual(normalize_title("曲­名​‌"), "曲名")

    def test_invisible_only_title_becomes_empty(self):
        self.assertEqual(normalize_title("­ ­ ​"), "")

    def test_non_str_title_is_converted_to_str(self):
        class Title:
            def __str__(self):
                return "全て12の所為です。"

        self.assertEqual(normalize_title(Title()), "全て12の所為です。")


class OgpTokenTest(SimpleTestCase):
    """make_ogp_token() / load_ogp_token() のテスト"""

    def test_round_trip(self):
        token = make_ogp_token("全て歌詞の所為です。")
        self.assertEqual(load_ogp_token(token), "全て歌詞の所為です。")

    def test_non_str_title_is_converted_to_str(self):
        # EditorViewはmetatitleにEditorのインスタンスを渡している
        class Title:
            def __str__(self):
                return "全て12の所為です。"

        self.assertEqual(load_ogp_token(make_ogp_token(Title())), "全て12の所為です。")

    def test_title_is_normalized(self):
        self.assertEqual(load_ogp_token(make_ogp_token("曲名\n­ 作者")), "曲名 作者")
        self.assertEqual(make_ogp_token("曲名\n作者"), make_ogp_token("曲名 作者"))

    def test_long_title_is_truncated(self):
        token = make_ogp_token("あ" * (OGP_TITLE_MAX_LENGTH + 50))
        self.assertEqual(load_ogp_token(token), "あ" * OGP_TITLE_MAX_LENGTH)

    def test_token_is_url_safe(self):
        token = make_ogp_token("全て歌詞の所為です。 / 全てあなたの所為です。")
        self.assertRegex(token, r"^[A-Za-z0-9_.:-]+$")

    def test_tampered_token_is_rejected(self):
        token = make_ogp_token("トップ")
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        with self.assertRaises(signing.BadSignature):
            load_ogp_token(tampered)

    def test_token_signed_with_other_salt_is_rejected(self):
        token = signing.dumps("トップ", compress=True)
        with self.assertRaises(signing.BadSignature):
            load_ogp_token(token)


class GetFontTest(SimpleTestCase):
    """get_font() のテスト"""

    # 文字を描き、描かれた範囲で切り抜く
    def draw_char(self, font, char):
        image = Image.new("L", (font.size * 2, font.size * 2), 0)
        ImageDraw.Draw(image).text((0, 0), char, font=font, fill=255)
        return image.crop(image.getbbox())

    def test_unsupported_char_is_drawn_as_tofu(self):
        # フォントに無い文字は.notdefのグリフで描かれる。.notdefが「ぎ」の形だったため豆腐にした（#212）
        font = get_font(TITLE_FONT_SIZES[0])
        # ハングル・絵文字・私用領域・未割り当て
        for char in ["한", "🎵", "\ue000", "\u0378"]:
            with self.subTest(char=hex(ord(char))):
                tofu = self.draw_char(font, char)

                # 中抜きの四角: 中央は描かれず、上下左右の辺の中点は描かれる
                width, height = tofu.size
                self.assertEqual(tofu.getpixel((width // 2, height // 2)), 0)
                for point in [(3, height // 2), (width - 4, height // 2), (width // 2, 3), (width // 2, height - 4)]:
                    self.assertEqual(tofu.getpixel(point), 255, point)


class WrapTextTest(SimpleTestCase):
    """wrap_text() のテスト"""

    def setUp(self):
        self.font = get_font(TITLE_FONT_SIZES[0])

    def test_short_text_is_one_line(self):
        self.assertEqual(wrap_text("トップ", self.font, TITLE_MAX_WIDTH), ["トップ"])

    def test_each_line_fits_max_width(self):
        lines = wrap_text("あ" * 40, self.font, TITLE_MAX_WIDTH)

        self.assertGreater(len(lines), 1)
        self.assertEqual("".join(lines), "あ" * 40)
        for line in lines:
            self.assertLessEqual(self.font.getlength(line), TITLE_MAX_WIDTH)

    def test_ascii_word_is_not_split(self):
        lines = wrap_text("Quick Brown", self.font, self.font.getlength("Quick Bro"))
        self.assertEqual(lines, ["Quick", "Brown"])

    def test_too_long_ascii_word_is_split_by_char(self):
        max_width = self.font.getlength("Supercali")
        lines = wrap_text("Supercalifragilistic", self.font, max_width)

        self.assertGreater(len(lines), 1)
        self.assertEqual("".join(lines), "Supercalifragilistic")
        for line in lines:
            self.assertLessEqual(self.font.getlength(line), max_width)

    def test_closing_punctuation_does_not_start_line(self):
        text = "あいうえお。かきくけこ、さしすせそ」たちつてと"
        for chars in range(3, 10):
            with self.subTest(chars=chars):
                lines = wrap_text(text, self.font, self.font.getlength("あ" * chars))
                self.assertEqual("".join(lines), text)
                for line in lines:
                    self.assertNotIn(line[0], "、。」")

    def test_breaks_at_space_in_latter_half(self):
        lines = wrap_text("全て歌詞の所為です。 / 全てあなたの所為です。", self.font, TITLE_MAX_WIDTH)
        self.assertEqual(lines, ["全て歌詞の所為です。 /", "全てあなたの所為です。"])

    def test_does_not_break_at_space_in_first_half(self):
        lines = wrap_text("A " + "あ" * 30, self.font, TITLE_MAX_WIDTH)
        self.assertTrue(lines[0].startswith("A あ"))


class LayoutTitleTest(SimpleTestCase):
    """layout_title() のテスト"""

    def test_short_title_uses_largest_font(self):
        font, lines = layout_title("トップ")

        self.assertEqual(font.size, TITLE_FONT_SIZES[0])
        self.assertEqual(lines, ["トップ"])

    def test_lines_fit_max_lines_and_height(self):
        for title in ["The Quick Brown Fox Jumps Over The Lazy Dog / Someone", "あ" * 60]:
            with self.subTest(title=title):
                font, lines = layout_title(title)

                self.assertLessEqual(len(lines), TITLE_MAX_LINES)
                self.assertLessEqual(get_text_height(font, len(lines)), TITLE_MAX_HEIGHT)
                for line in lines:
                    self.assertLessEqual(font.getlength(line), TITLE_MAX_WIDTH)

    def test_too_long_title_is_truncated_with_ellipsis(self):
        font, lines = layout_title("あ" * OGP_TITLE_MAX_LENGTH)

        self.assertEqual(font.size, TITLE_FONT_SIZES[-1])
        self.assertEqual(len(lines), TITLE_MAX_LINES)
        self.assertTrue(lines[-1].endswith("…"))
        self.assertLessEqual(font.getlength(lines[-1]), TITLE_MAX_WIDTH)


class RenderOgpImageTest(SimpleTestCase):
    """render_ogp_image() のテスト"""

    def test_returns_1200x630_png(self):
        image = Image.open(io.BytesIO(render_ogp_image("トップ")))

        self.assertEqual(image.format, "PNG")
        self.assertEqual(image.size, (1200, 630))

    def test_different_titles_make_different_images(self):
        self.assertNotEqual(render_ogp_image("トップ"), render_ogp_image("統計"))

    def test_title_is_normalized_before_drawing(self):
        # 改行を含む文字列をそのまま描くと複数行のテキストとして扱われ、位置がずれるため
        self.assertEqual(render_ogp_image("曲名\n­作者"), render_ogp_image("曲名 作者"))

    def test_drawing_is_serialized_by_lock(self):
        # FreeTypeのフォントを複数のスレッドから同時に使わないよう、描画はロックの中で行う
        with patch("subekashi.lib.ogp.RENDER_LOCK") as lock:
            render_ogp_image("トップ")
        lock.__enter__.assert_called_once()
        lock.__exit__.assert_called_once()

    def test_concurrent_rendering_makes_same_image(self):
        title = "全て歌詞の所為です。 / 全てあなたの所為です。"
        expected = render_ogp_image(title)
        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(render_ogp_image, [title] * 8))
        self.assertEqual(results, [expected] * 8)

    def test_title_does_not_overlap_logo(self):
        # タイトルが最大の高さでも、タイトル・下線とロゴの間に何も描かれない帯が残る
        background = Image.new("RGB", (1, 1), BACKGROUND_COLOR).getpixel((0, 0))
        for title in ["The Quick Brown Fox Jumps Over The Lazy Dog / Someone", "あ" * OGP_TITLE_MAX_LENGTH]:
            with self.subTest(title=title):
                image = Image.open(io.BytesIO(render_ogp_image(title))).convert("RGB")
                band = image.crop((0, 480, 1200, 520))
                self.assertEqual(band.getcolors(), [(1200 * 40, background)])
