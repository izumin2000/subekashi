from subekashi.constants.constants import ALLOW_MEDIAS, ALL_MEDIAS
from config.local_settings import ERROR_DISCORD_URL
from subekashi.lib.discord import send_discord
from urllib.parse import urlparse, urlunparse, parse_qs
import re

_YOUTUBE_RE = re.compile(
    r'https?://(?:www\.|m\.)?(?:youtube\.com/(?:.*[?&]v=|shorts/|live/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
)

# av番号は、BV番号に変換できる2^51未満（15桁以下）のみ対象にする
_BILIBILI_VIDEO_PATH_RE = re.compile(r'/video/(?:(BV1[0-9A-Za-z]{9})|av([1-9][0-9]{0,14}))/?')
_BILIBILI_BV_ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
_BILIBILI_BV_ORDER = (8, 7, 0, 5, 1, 3, 2, 4, 6)

_ALLOW_MEDIA_RES = [(re.compile(m["regex"]), m) for m in ALLOW_MEDIAS]
_ALL_MEDIA_RES = [(re.compile(m["regex"]), m) for m in ALL_MEDIAS]


# YouTubeの動画URLかどうか
def is_youtube_url(url):
    return _YOUTUBE_RE.search(url) is not None


def get_youtube_id(url):
    match = _YOUTUBE_RE.search(url)
    return match.group(1) if match else url


# YouTubeの動画URLを短縮する
def format_youtube_url(url):
    match = _YOUTUBE_RE.search(url)
    if not match:
        return url
    return f"https://youtu.be/{match.group(1)}"


# XのURLのクエリを削除
def format_x_url(url):
    parsed_url = urlparse(url)

    # X/TwitterのURLのみ処理
    if parsed_url.netloc not in ('twitter.com', 'x.com'):
        return url

    return urlunparse(parsed_url._replace(scheme='https', netloc='x.com', query='', fragment=''))


# ビリビリ動画のav番号をBV番号に変換する
def convert_av_to_bv(aid):
    code = ((1 << 51) | aid) ^ 23442827791579
    chars = [""] * 9
    for i in _BILIBILI_BV_ORDER:
        code, rest = divmod(code, 58)
        chars[i] = _BILIBILI_BV_ALPHABET[rest]
    return "BV1" + "".join(chars)


# ビリビリ動画の動画のURLを「https://bilibili.com/video/BV<id>」に揃える（#1246）
# av番号はBV番号に変換する。複数のパートがある動画は、パートごとに別の曲のことがあるため、2パート目以降の「?p=<n>」のみ残す
def format_bilibili_url(url):
    parsed_url = urlparse(url)

    if parsed_url.netloc not in ('bilibili.com', 'www.bilibili.com', 'm.bilibili.com'):
        return url

    match = _BILIBILI_VIDEO_PATH_RE.fullmatch(parsed_url.path)
    if not match:
        return url

    bvid = match.group(1) or convert_av_to_bv(int(match.group(2)))
    page = parse_qs(parsed_url.query).get('p', [''])[0].lstrip('0')
    query = f"p={page}" if page.isdecimal() and page != '1' else ''
    return urlunparse(('https', 'bilibili.com', f'/video/{bvid}', '', query, ''))


# URLを短縮しフォーマットする
def clean_url(urls):
    urls = urls.replace(" ,", ",").replace(", ", ",")
    urls = urls.replace("//www.", "//")
    urls = urls.replace("https://www.google.com/url?q=", "")
    url_list = urls.split(",")
    url_list = list(map(format_youtube_url, url_list))
    url_list = list(map(format_x_url, url_list))
    url_list = list(map(format_bilibili_url, url_list))
    url_list = [u.rstrip('/') for u in url_list]
    return ",".join(url_list)


# urlが許可されているドメインならその情報を返す
# 許可されていないならFalseを返す
def get_allow_media(url):
    domain = urlparse(url).netloc

    for pattern, media in _ALLOW_MEDIA_RES:
        if pattern.search(domain):
            return media

    return False


# 全urlのドメインの情報を返す
# Falseを返すことはない
def get_all_media(url):
    domain = urlparse(url).netloc
    last_index = len(_ALL_MEDIA_RES) - 1

    for i, (pattern, media) in enumerate(_ALL_MEDIA_RES):
        if not pattern.search(domain):
            continue

        # 最後のエントリは想定外URLのフォールバック
        if i == last_index:
            send_discord(ERROR_DISCORD_URL, f"想定外のURLが添付されました：{url}")

        return media

    send_discord(ERROR_DISCORD_URL, "get_all_mediaにエラーが発生しました")
    return False