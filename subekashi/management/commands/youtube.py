from django.core.management.base import BaseCommand
from config.settings import *
from subekashi.lib.url import *
from subekashi.models import Song
from googleapiclient.discovery import build
from datetime import datetime
from time import sleep


class Command(BaseCommand):
    help = "YouTube API関連。idオプションを加えることでそのidのみのsongレコードを更新する"
    
    def get_youtube_links(self, song):
        urls = song.url.split(",")
        video_ids = [format_yt_url(url, True) for url in urls if is_yt_link(url)]
        return video_ids
    
    def get_youtube_api(self, video_id):
        sleep(2)
        yt_res = {}
        
        try:
            youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            
            request = youtube.videos().list(
                part="snippet,statistics",
                id=video_id
            )
            response = request.execute()
            
            item = response["items"][0]
            
            statistics = item["statistics"]
            yt_res["view"] = int(statistics["viewCount"])
            if not "likeCount" in statistics:
                yt_res["like"] = int(statistics["favoriteCount"])
            else:
                yt_res["like"] = int(statistics["likeCount"])
            upload_time = item["snippet"]["publishedAt"]
            upload_time = datetime.strptime(upload_time, "%Y-%m-%dT%H:%M:%SZ")
            yt_res["upload_time"] = upload_time
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"エラー：{e}"))
            
        return yt_res
    
    def get_best_youtube_view(self, songs):
        best_view = 0
        video_ids = self.get_youtube_links(songs)
        best_res = {}

        for video_id in video_ids:
            yt_res = self.get_youtube_api(video_id)
            view = yt_res.get("view", 0)
            like = yt_res.get("like", 0)
            upload_time = yt_res.get("upload_time", None)
            if view > best_view:
                best_view = view
                best_res["view"] = view
                best_res["like"] = like
                best_res["upload_time"] = upload_time
        return best_res
    
    def save_song(self, song, best_res):
        if not any(best_res):
            return
        
        song.view = best_res.get("view", 0)
        song.like = best_res.get("like", 0)
        song.upload_time = best_res.get("upload_time", None)
        song.save()
        self.stdout.write(self.style.SUCCESS(f"{str(song.id).zfill(4)}({song.title})のYouTube情報：{best_res}"))
    
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