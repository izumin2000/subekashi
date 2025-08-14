from django.core.management.base import BaseCommand
from config.settings import ROOT_URL
from subekashi.models import Song
from subekashi.lib.url import *
from collections import Counter

class Command(BaseCommand) :
    def handle(self, *args, **options):
        # Songに登録されカンマ区切りされた全URLのリスト
        urls = sum([url.split(',') for url in Song.objects.values_list("url", flat=True)], [])
        
        is_all_unique = True
        for url, count in Counter(urls).items():
            # 重複しているURLが無かったらスキップ
            if count <= 1:
                continue
            
            print(f"{ROOT_URL}/songs/?url={url}")
            is_all_unique = False
                
        if is_all_unique :
            print("URLの重複は見つかりませんでした。")

