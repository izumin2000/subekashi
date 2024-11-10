from django.core.management.base import BaseCommand
from subekashi.lib.url import *
from subekashi.lib.youtube import *
from subekashi.models import Song


class Command(BaseCommand):
    help = "YouTube API関連。idオプションを加えることでそのidのみのsongレコードを更新する"
    
    def get_youtube_links(self, song):
        urls = song.url.split(",")
        video_ids = [format_yt_url(url, True) for url in urls if is_yt_url(url)]
        return video_ids
    
    def get_best_youtube_view(self, songs):
        best_view = 0
        is_deleted = True
        video_ids = self.get_youtube_links(songs)
        best_res = {}

        for video_id in video_ids:
            yt_res = get_youtube_api(video_id)
            if yt_res == {}:
                continue
            
            is_deleted = False
            view = yt_res.get("view", 0)
            like = yt_res.get("like", 0)
            upload_time = yt_res.get("upload_time", None)
            if view > best_view:
                best_view = view
                best_res["view"] = view
                best_res["like"] = like
                best_res["upload_time"] = upload_time
        
        best_res["is_deleted"] = is_deleted
        return best_res
    
    def save_song(self, song, best_res):
        song.isdeleted = best_res.get("is_deleted", False)
        
        song.view = best_res.get("view", 0)
        song.like = best_res.get("like", 0)
        song.upload_time = best_res.get("upload_time", None)
        song.save()
    
    def handle(self, *args, **options) :
        id = options["id"]
        if id:
            song = Song.objects.get(pk = id)
            best_res = self.get_best_youtube_view(song)
            self.save_song(song, best_res)
            return
        
        for song in Song.objects.all():
            best_res = self.get_best_youtube_view(song)
            self.save_song(song, best_res)
        
    def add_arguments(self, parser):
        parser.add_argument("-id", required=False, type=int)