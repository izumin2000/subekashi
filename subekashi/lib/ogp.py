import io
import os
import re
import threading
import unicodedata
from functools import lru_cache
from django.conf import settings
from django.core import signing
from PIL import Image, ImageDraw, ImageFont

OGP_SALT = "subekashi.ogp"
OGP_TITLE_MAX_LENGTH = 100
# 画像のURLに付けるバージョン。画像は1年間キャッシュさせるため、デザインを変えたら上げる
OGP_VERSION = 2

WIDTH, HEIGHT = 1200, 630
BACKGROUND_COLOR = "#111"
TEXT_COLOR = "#fff"

TITLE_MAX_WIDTH = 1040
TITLE_MAX_HEIGHT = 240
TITLE_MAX_LINES = 3
TITLE_FONT_SIZES = [80, 72, 64, 56]
TITLE_LINE_HEIGHT = 1.3
UNDERLINE_WIDTH = 260
UNDERLINE_HEIGHT = 12
UNDERLINE_MARGIN = 34

SITE_NAME = "全て歌詞の所為です。"
LOGO_ICON_SIZE = 64
LOGO_FONT_SIZE = 40
LOGO_GAP = 18
LOGO_CENTER_Y = 562

FONT_PATH = os.path.join(settings.BASE_DIR, "subekashi/static/subekashi/fonts/GenZenGothicKaiC.woff2")
ICON_PATH = os.path.join(settings.BASE_DIR, "subekashi/static/subekashi/image/icon_large.png")

# FreeTypeのフォントは複数のスレッドから同時に使うと安全でないため、描画は1枚ずつ行う（runserverはスレッドで動く）
RENDER_LOCK = threading.Lock()

# 英数字の連続は単語として扱い途中で折り返さない。行頭禁則の約物は直前の文字とまとめる
TOKEN_PATTERN = re.compile(r"\s+|(?:[!-~]+|.)[、。，．」』）】！？ー…]*")


# 改行や連続した空白は1つの空白にまとめ、ソフトハイフン・ゼロ幅スペースなどの見えない文字（書式文字）は取り除く。
# 見えない文字はブラウザでは表示されないが、フォントによっては画像に記号として描かれるため
def normalize_title(title):
    visible = "".join(char for char in str(title) if unicodedata.category(char) != "Cf")
    return " ".join(visible.split())


def make_ogp_token(title):
    return signing.dumps(normalize_title(title)[:OGP_TITLE_MAX_LENGTH], salt=OGP_SALT, compress=True)


def load_ogp_token(token):
    return signing.loads(token, salt=OGP_SALT)


@lru_cache(maxsize=None)
def get_font(size):
    return ImageFont.truetype(FONT_PATH, size)


@lru_cache(maxsize=None)
def get_logo_icon():
    scale = 4
    icon = Image.open(ICON_PATH).convert("RGB").resize((LOGO_ICON_SIZE, LOGO_ICON_SIZE), Image.LANCZOS)
    mask = Image.new("L", (LOGO_ICON_SIZE * scale, LOGO_ICON_SIZE * scale), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, mask.width - 1, mask.height - 1), fill=255)
    return icon, mask.resize((LOGO_ICON_SIZE, LOGO_ICON_SIZE), Image.LANCZOS)


def wrap_text(text, font, max_width):
    lines = [""]
    for token in TOKEN_PATTERN.findall(text):
        if font.getlength(lines[-1] + token) <= max_width:
            lines[-1] += token
        elif token.isspace():
            lines.append("")
        else:
            # 行の後半に空白があれば、そこで折り返す（「曲名 / 作者名」の区切りなど）
            head, space, tail = lines[-1].rpartition(" ")
            if space and font.getlength(head) >= max_width / 2:
                lines[-1] = head
                lines.append(tail)
            elif lines[-1].strip():
                lines.append("")
            for char in token:
                if lines[-1] and font.getlength(lines[-1] + char) > max_width:
                    lines.append("")
                lines[-1] += char
    return [line.strip() for line in lines if line.strip()]


def get_line_height(font):
    return round(font.size * TITLE_LINE_HEIGHT)


def get_text_height(font, line_count):
    return font.size + get_line_height(font) * (line_count - 1)


def layout_title(title):
    for size in TITLE_FONT_SIZES:
        font = get_font(size)
        lines = wrap_text(title, font, TITLE_MAX_WIDTH)
        if len(lines) <= TITLE_MAX_LINES and get_text_height(font, len(lines)) <= TITLE_MAX_HEIGHT:
            return font, lines

    # どのサイズでも収まらない場合は、最小のサイズで最大の行数までにし、最終行を「…」で省略する
    font = get_font(TITLE_FONT_SIZES[-1])
    lines = wrap_text(title, font, TITLE_MAX_WIDTH)[:TITLE_MAX_LINES]
    last_line = lines[-1]
    while last_line and font.getlength(last_line + "…") > TITLE_MAX_WIDTH:
        last_line = last_line[:-1]
    lines[-1] = last_line + "…"
    return font, lines


def render_ogp_image(title):
    with RENDER_LOCK:
        image = draw_ogp_image(normalize_title(title))

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def draw_ogp_image(title):
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)

    # タイトルと下線をまとめて上下中央に置く。タイトルの高さは1行目の上端から最終行の下端まで（行間を含めない）
    font, lines = layout_title(title)
    line_height = get_line_height(font)
    text_height = get_text_height(font, len(lines))
    top = (HEIGHT - (text_height + UNDERLINE_MARGIN + UNDERLINE_HEIGHT)) // 2
    for i, line in enumerate(lines):
        draw.text((WIDTH // 2, top + font.size // 2 + line_height * i), line, font=font, fill=TEXT_COLOR, anchor="mm")
    underline_top = top + text_height + UNDERLINE_MARGIN
    underline_left = (WIDTH - UNDERLINE_WIDTH) // 2
    draw.rectangle(
        (underline_left, underline_top, underline_left + UNDERLINE_WIDTH - 1, underline_top + UNDERLINE_HEIGHT - 1),
        fill=TEXT_COLOR,
    )

    # 下部にロゴと「全て歌詞の所為です。」を並べる
    logo_font = get_font(LOGO_FONT_SIZE)
    logo_width = LOGO_ICON_SIZE + LOGO_GAP + logo_font.getlength(SITE_NAME)
    logo_left = round((WIDTH - logo_width) / 2)
    icon, mask = get_logo_icon()
    image.paste(icon, (logo_left, LOGO_CENTER_Y - LOGO_ICON_SIZE // 2), mask)
    draw.text((logo_left + LOGO_ICON_SIZE + LOGO_GAP, LOGO_CENTER_Y), SITE_NAME, font=logo_font, fill=TEXT_COLOR, anchor="lm")
    return image
