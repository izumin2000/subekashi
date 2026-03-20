from subekashi.constants.constants import ALLOW_MEDIAS, ALL_MEDIAS
from config.local_settings import ERROR_DISCORD_URL
from subekashi.lib.discord import send_discord
from urllib.parse import urlparse, urlunparse
import re

_YOUTUBE_RE = re.compile(
    r'https?://(?:www\.|m\.)?(?:youtube\.com/(?:.*[?&]v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})'
)


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


# URLを短縮しフォーマットする
def clean_url(urls):
    urls = urls.replace(" ,", ",").replace(", ", ",")
    urls = urls.replace("//www.", "//")
    urls = urls.replace("https://www.google.com/url?q=", "")
    url_list = urls.split(",")
    url_list = list(map(format_youtube_url, url_list))
    url_list = list(map(format_x_url, url_list))
    return ",".join(url_list)


# TODO: ALLOW_MEDIAS / ALL_MEDIAS の regex をモジュールロード時にコンパイルしてホットパスの re.search コストを削減する
# urlが許可されているドメインならその情報を返す
# 許可されていないならFalseを返す
def get_allow_media(url):
    domain = urlparse(url).netloc

    for media in ALLOW_MEDIAS:
        if re.search(media["regex"], domain):
            return media

    return False


# 全urlのドメインの情報を返す
# Falseを返すことはない
def get_all_media(url):
    domain = urlparse(url).netloc
    last_index = len(ALL_MEDIAS) - 1

    for i, media in enumerate(ALL_MEDIAS):
        if not re.search(media["regex"], domain):
            continue

        # 最後のエントリは想定外URLのフォールバック
        if i == last_index:
            send_discord(ERROR_DISCORD_URL, f"想定外のURLが添付されました：{url}")

        return media

    send_discord(ERROR_DISCORD_URL, "get_all_mediaにエラーが発生しました")
    return False