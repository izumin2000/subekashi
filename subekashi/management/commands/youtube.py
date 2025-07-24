from django.core.management.base import BaseCommand
from subekashi.lib.url import *
from subekashi.lib.youtube import *
from subekashi.models import Song
from time import sleep


class Command(BaseCommand):
    help = "YouTube API関連。idオプションを加えることでそのidのみのsongレコードを更新する"
    
    # song.urlから(複数の)YouTube動画IDを取得しリストにする
    def get_youtube_ids(self, song):
        urls = song.url.split(",")
        video_ids = [get_youtube_id(url) for url in urls if is_youtube_url(url)]
        return video_ids
    
    # 複数のYouTubeの動画の再生回数・高評価数の総和を求める
    # アップロード日時は最も新しい日時を取得する
    def get_youtube_info_sum(self, songs):
        is_deleted = True
        video_ids = self.get_youtube_ids(songs)
        upload_time_list = []
        info = {
            "view": 0,
            "like": 0
        }
        
        # song.urlに1つもYouTubeの動画が無かったら
        if not video_ids :
            return {}

        # 複数のYouTubeの動画を1つずつ確認する
        for video_id in video_ids:
            sleep(2)
            res = get_youtube_api(video_id)
            
            # APIを取得できなかったら
            if res == {}:
                continue
            
            is_deleted = False      # 公開していたら
            
            # 再生回数と高評価数を総和に追加
            info["view"] += res.get("view", 0)
            info["like"] += res.get("like", 0)
            
            # upload_time_listにアップロード日時を追加
            upload_time = res.get("upload_time", None)
            if upload_time :
                upload_time_list.append(upload_time)
                
        info["is_deleted"] = is_deleted
        info["upload_time"] = max(upload_time_list) if upload_time_list else None
        return info
    
    # Songモデルにinfoの内容を保存
    def save_song(self, song, info):
        song.view = info.get("view", 0)
        song.like = info.get("like", 0)
        song.upload_time = info.get("upload_time", None)
        song.isdeleted = info.get("is_deleted", False)
        song.save()
    
    def handle(self, *args, **options) :
        id = options["id"]
        
        # song_idが指定されていたら
        if id:
            song = Song.objects.get(pk = id)
            info = self.get_youtube_info_sum(song)
            if not info:
                return
            
            self.save_song(song, info)
            return
        
        # 全てのsongが対象なら
        for song in Song.objects.exclude(url = ""):
            info = self.get_youtube_info_sum(song)
            if not info:
                continue
            
            self.save_song(song, info)
        
    def add_arguments(self, parser):
        parser.add_argument("-id", required=False, type=int)