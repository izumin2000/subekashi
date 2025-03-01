from django.core.management.base import BaseCommand
from subekashi.models import Song
from subekashi.lib.url import *
from collections import Counter

class Command(BaseCommand) :
    def handle(self, *args, **options):
        urls = sum([url.split(',') for url in Song.objects.values_list("url", flat=True)], [])       # Songに登録されカンマ区切りされた全URLのリスト
        youtube_id_list = []    # YouTubeの動画リスト
        for url in urls :
            if is_yt_url(url):      # URLがYouTubeの動画URLなら
                youtube_id = get_youtube_id(url)
                youtube_id_list.append(youtube_id)
        
        is_dup = False
        for id, count in Counter(youtube_id_list).items():
            if count > 1:       # 重複している動画IDがあったら
                print(f"https://lyrics.imicomweb.com/search?url={id}")
                is_dup = True
                
        if not is_dup :
            print("重複は見つかりませんでした。")

