from django.core.management.base import BaseCommand
from subekashi.models import *
import re
from collections import Counter


URL_PATTERN = r'(?:\/|v=)([A-Za-z0-9_-]{11})(?:\?|&|$)'


def re_yt_url(url):
    match = re.search(URL_PATTERN, url)
    return match    


def is_yt_url(url):
    match = re_yt_url(url)
    return not match is None


def format_yt_url(url, id=False):
    match = re_yt_url(url)
    if match is None:
        return url
    videoID = match.group(1)
    if id:
        return videoID
    return "https://youtu.be/" + videoID

class Command(BaseCommand) :
    def handle(self, *args, **options):
        urls = Song.objects.values_list("url", flat=True)
        ids = []
        for url in urls :       # 各レコードのurlごとに
            for one_url in url.split(",") :     # 1つのレコードの各urlごとに
                if is_yt_url(one_url):      # URLがYouTubeなら
                    id = format_yt_url(one_url, id=True)
                    ids.append(id)
        
        is_dup = False
        for id, count in Counter(ids).items():      # 
            if count > 1:
                print(f"https://lyrics.imicomweb.com/search?url={id}")
                is_dup = True
        if not is_dup :
            print("重複は見つかりませんでした。")

