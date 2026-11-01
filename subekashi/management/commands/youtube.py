from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from config.local_settings import ERROR_DISCORD_URL
from subekashi.lib.discord import send_discord
from subekashi.lib.url import *
from subekashi.lib.youtube import *
from subekashi.models import Song
from time import sleep


class Command(BaseCommand):
    help = (
        "YouTube API関連。idオプションを加えることでそのidのみのsongレコードを更新する。"
        "idオプションが無い場合は、偶数日はidが偶数、奇数日はidが奇数のsongレコードのみを更新する"
    )
    
    # URLの中からYouTubeの動画IDを取得する
    def get_video_ids(self, urls):
        return [get_youtube_id(url) for url in urls if is_youtube_url(url)]

    # 動画をYOUTUBE_API_MAX_IDS件ずつまとめて取得する
    # 取得できた動画の情報・取得に失敗した動画のエラー・以降の呼び出しも全て失敗するエラー（無ければNone）を返す
    def fetch_video_infos(self, video_ids):
        video_infos = {}
        failed_errors = {}

        for i in range(0, len(video_ids), YOUTUBE_API_MAX_IDS):
            chunk = video_ids[i:i + YOUTUBE_API_MAX_IDS]
            sleep(2)

            try:
                video_infos.update(get_youtube_api_batch(chunk))

            # 以降の呼び出しも全て失敗するため、残りの動画の取得を打ち切る
            except YoutubeApiUnavailableError as e:
                return video_infos, failed_errors, e

            except YoutubeApiError as e:
                failed_errors.update({video_id: e for video_id in chunk})

        return video_infos, failed_errors, None

    # 複数のYouTubeの動画の再生回数・高評価数の総和を求める
    # アップロード日時は最も新しい日時を取得する
    def get_youtube_info_sum(self, urls, video_infos):
        is_deleted = True
        video_ids = self.get_video_ids(urls)
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
            res = video_infos[video_id]

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
            if not Song.objects.filter(pk=id).exists():
                raise CommandError(f"song_id：{id}の曲は存在しません")
            song_ids = [id]
        else:
            all_song_ids = list(
                Song.objects.filter(links__isnull=False).distinct().order_by('pk').values_list('pk', flat=True)
            )

            # YouTube Data APIのクォータ枯渇対策として、偶数日はidが偶数、奇数日はidが奇数のsongのみを対象にする
            parity = timezone.localtime(timezone.now()).day % 2
            song_ids = [song_id for song_id in all_song_ids if song_id % 2 == parity]

        # 動画をまとめて取得するため、先に全てのsongのURLを取得する
        urls_by_song_id = {}
        for song_id in song_ids:
            song = Song.objects.filter(pk=song_id).first()
            if song is None:
                continue
            urls_by_song_id[song_id] = list(song.links.values_list('url', flat=True))

        # 複数のsongに紐づく動画は1回だけ取得する
        video_ids = list(dict.fromkeys(
            video_id for urls in urls_by_song_id.values() for video_id in self.get_video_ids(urls)
        ))
        video_infos, failed_errors, unavailable_error = self.fetch_video_infos(video_ids)

        # 取得できた動画の分だけsongを更新するため、通知してもここでは終了しない
        if unavailable_error:
            message = f"{unavailable_error}。youtubeコマンドの処理を打ち切りました（動画{len(video_ids)}件のうち{len(video_infos)}件を取得済み）"
            self.stderr.write(self.style.ERROR(message))
            send_discord(ERROR_DISCORD_URL, message)

        for song_id, urls in urls_by_song_id.items():
            # 全件処理は時間がかかるため、処理中に削除された曲はスキップする
            song = Song.objects.filter(pk=song_id).first()
            if song is None:
                continue

            song_video_ids = self.get_video_ids(urls)

            # 1本でも取得に失敗した曲は、公開状況・再生回数などが不正確になるため更新しない
            errors = [failed_errors[video_id] for video_id in song_video_ids if video_id in failed_errors]
            if errors:
                self.stderr.write(self.style.WARNING(f"{errors[0]}。更新をスキップしました（song_id：{song_id}）"))
                continue

            # 取得を打ち切ったため1本でも取得できていない曲も、同様に更新しない
            if any(video_id not in video_infos for video_id in song_video_ids):
                continue

            info = self.get_youtube_info_sum(urls, video_infos)
            if not info:
                continue
            self.save_song(song, info)
        
    def add_arguments(self, parser):
        parser.add_argument("-id", required=False, type=int)
