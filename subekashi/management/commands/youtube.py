from django.core.management.base import BaseCommand
from config.local_settings import ERROR_DISCORD_URL
from subekashi.lib.discord import send_discord
from subekashi.lib.url import *
from subekashi.lib.youtube import *
from subekashi.models import Song
from time import sleep


class Command(BaseCommand):
    help = "YouTube API関連。idオプションを加えることでそのidのみのsongレコードを更新する"
    
    # 複数のYouTubeの動画の再生回数・高評価数の総和を求める
    # アップロード日時は最も新しい日時を取得する
    def get_youtube_info_sum(self, song):
        is_deleted = True
        urls = list(song.links.values_list('url', flat=True))
        video_ids = [get_youtube_id(url) for url in urls if is_youtube_url(url)]
        has_other_url = any(not is_youtube_url(url) for url in urls)
        upload_time_list = []
        info = {
            "view": 0,
            "like": 0
        }

        # SongLinkに1つもYouTubeの動画が無かったら
        if not video_ids:
            return {}

        # 複数のYouTubeの動画を1つずつ確認する
        for video_id in video_ids:
            sleep(2)
            res = get_youtube_api(video_id)
            
            # 動画が削除・非公開なら
            if res == {}:
                continue
            
            is_deleted = False      # 公開していたら
            
            # 再生回数と高評価数を総和に追加
            info["view"] += res.get("view", 0)
            info["like"] += res.get("like", 0)
            
            # upload_time_listにアップロード日時を追加
            upload_time = res.get("upload_time", None)
            if upload_time:
                upload_time_list.append(upload_time)
                
        # YouTubeの動画が全て取得できなかったら、再生回数・高評価数・アップロード日時は前回の値を引き継ぐ
        if is_deleted:
            # YouTube以外のURLは公開状況を確認できないため、削除済みかどうかも変更しない
            if has_other_url:
                return {}
            return {"is_deleted": True}

        info["upload_time"] = max(upload_time_list) if upload_time_list else None
        info["is_deleted"] = is_deleted
        return info

    # Songモデルにinfoの内容を保存
    def save_song(self, song, info):
        song.view = info.get("view", song.view)
        song.like = info.get("like", song.like)
        song.upload_time = info.get("upload_time", song.upload_time)
        song.is_deleted = info.get("is_deleted", song.is_deleted)
        song.save()
    
    def handle(self, *args, **options):
        id = options["id"]
        
        # song_idが指定されていたらそのsongのみ、指定されていなければ全てのsongが対象（SongLinkが存在するSongのみ）
        # IDを先に全件取得してカーソルを閉じることでDBロックを防ぐ
        if id:
            song_ids = [id]
        else:
            song_ids = list(
                Song.objects.filter(links__isnull=False).distinct().values_list('pk', flat=True)
            )

        for song_id in song_ids:
            song = Song.objects.get(pk=song_id)
            try:
                info = self.get_youtube_info_sum(song)

            # 以降の呼び出しも全て失敗するため、残りの曲の処理を打ち切る
            except YoutubeApiUnavailableError as e:
                message = f"{e}。youtubeコマンドの処理を打ち切りました（song_id：{song_id}）"
                self.stderr.write(self.style.ERROR(message))
                send_discord(ERROR_DISCORD_URL, message)
                return

            # 1本でも取得に失敗した曲は、公開状況・再生回数などが不正確になるため更新しない
            except YoutubeApiError as e:
                self.stderr.write(self.style.WARNING(f"{e}。更新をスキップしました（song_id：{song_id}）"))
                continue

            if not info:
                continue
            self.save_song(song, info)
        
    def add_arguments(self, parser):
        parser.add_argument("-id", required=False, type=int)