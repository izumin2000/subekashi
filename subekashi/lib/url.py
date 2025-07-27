from subekashi.constants.constants import ALLOW_MEDIAS, ALL_MEDIAS
from config.local_settings import ERROR_DISCORD_URL
from subekashi.lib.discord import send_discord
from urllib.parse import urlparse, urlunparse
import re


# TODO リファクタリング
# YouTubeの動画IDのパターンマッチ
def re_youtube_url(url):
    match = re.search(r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:.*[?&]v=|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    return match    

# YouTubeの動画URLかどうか
def is_youtube_url(url):
    match = re_youtube_url(url)
    return not match is None

def get_youtube_id(url):
    # もしYouTubeの動画IDではなかったら
    if not is_youtube_url(url):
        return url
    
    match = re_youtube_url(url)
    return match.group(1)

# YouTubeの動画URLを短縮する
def format_youtube_url(url):
    # もしYouTubeの動画IDではなかったら
    if not is_youtube_url(url):
        return url
    
    return f"https://youtu.be/{get_youtube_id(url)}"

# XのURLのクエリを削除
def format_x_url(url):
    parsed_url = urlparse(url)
    clean_url = urlunparse(parsed_url._replace(query='', fragment=''))
    return clean_url

# URLを短縮しフォーマットする
def clean_url(urls):
    urls = urls.replace(" ,", ",").replace(", ", ",")
    urls = urls.replace("https://www.google.com/url?q=", "")
    urls = urls.replace("https://www.", "https://")
    urls = urls.replace("https://twitter.com", "https://x.com")
    url_list = urls.split(",")
    url_list = list(map(format_youtube_url, url_list))
    url_list = list(map(format_x_url, url_list))
    return ",".join(url_list)

# urlが許可されているドメインならその情報を返す
# 許可されていないならFalseを返す
def get_allow_media(url):
    domain = urlparse(url).netloc
    
    for i, media in enumerate(ALLOW_MEDIAS):
        if bool(re.search(media["regex"], domain)):
            return ALLOW_MEDIAS[i]
    
    return False

# 全urlのドメインの情報を返す
# Falseを返すことはない
def get_all_media(url):
    domain = urlparse(url).netloc
    allow_medias_size = len(ALL_MEDIAS)
    
    for i, media in enumerate(ALL_MEDIAS):
        re_allow = re.search(media["regex"], domain)
        
        # URLが許可されているのならそのドメイン情報を返す
        if bool(re_allow) and ((i + 1) != allow_medias_size):
            return ALL_MEDIAS[i]
        
        # URLが許可されていないのならdiscrodに通知してそのドメイン情報を返す
        if bool(re_allow) and ((i + 1) == allow_medias_size):
            send_discord(ERROR_DISCORD_URL, f"想定外のURLが添付されました：{url}")
            return ALL_MEDIAS[i]
    
    send_discord(ERROR_DISCORD_URL, f"get_all_mediaにエラーが発生しました")
    return False