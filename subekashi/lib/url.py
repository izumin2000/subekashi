from subekashi.constants.constants import *
from urllib.parse import urlparse, urlunparse
import re


# YouTubeの動画IDのパターンマッチ
def re_yt_url(url):
    match = re.search(r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/.*[?&]v=|youtu\.be\/)([a-zA-Z0-9_-]{11})', url)
    return match    

# YouTubeの動画URLかどうか
def is_yt_url(url):
    match = re_yt_url(url)
    return not match is None

def get_youtube_id(url):
    # もしYouTubeの動画IDではなかったら
    if not is_yt_url(url):
        return url
    
    match = re_yt_url(url)
    return match.group(1)

# YouTubeの動画URLを短縮する
def format_yt_url(url):
    # もしYouTubeの動画IDではなかったら
    if not is_yt_url(url):
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
    url_list = list(map(format_yt_url, url_list))
    url_list = list(map(format_x_url, url_list))
    return ",".join(url_list)