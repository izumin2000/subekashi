from googleapiclient.discovery import build
from config.settings import YOUTUBE_API_KEY
from datetime import datetime
import pytz

def get_youtube_api(video_id):
    try:
        # YOUTUBE_API_KEYが空なら
        if YOUTUBE_API_KEY == "":
            return {}
        
        # YouTubeからデータを取得
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.videos().list(
            part="snippet,statistics,liveStreamingDetails",
            id=video_id
        )
        response = request.execute()
        
        item = response["items"][0]
        statistics = item["statistics"]
        snippet = item["snippet"]
        
        # プレミア公開日時か投稿日時を取得
        if "liveBroadcastContent" in snippet and snippet["liveBroadcastContent"] == "upcoming":
            publish_time = snippet.get("scheduledPublishTime") or item.get("liveStreamingDetails", {}).get("scheduledStartTime")       # 親の日時
        else:
            publish_time = snippet["publishedAt"]       # 投稿日時

        # 日本標準時の投稿日時を取得
        upload_time_str = datetime.strptime(publish_time, "%Y-%m-%dT%H:%M:%SZ")

        utc_zone = pytz.utc
        jst_zone = pytz.timezone("Asia/Tokyo")
        jst_upload_time = utc_zone.localize(upload_time_str).astimezone(jst_zone)
        
        # チャンネル名を取得（複数チャンネルに対応）
        channels = []

        # 主チャンネル名を取得
        if "channelTitle" in snippet:
            channels.append(snippet["channelTitle"])

        # 複数チャンネル対応（collaboration等）
        # YouTubeの新しいAPIでは複数チャンネルがある場合があるため、
        # 様々なフィールドをチェック
        if "channelTitles" in snippet:
            # channelTitlesがリストの場合
            if isinstance(snippet["channelTitles"], list):
                for ch in snippet["channelTitles"]:
                    if ch not in channels:
                        channels.append(ch)
            # channelTitlesが文字列の場合
            elif isinstance(snippet["channelTitles"], str):
                if snippet["channelTitles"] not in channels:
                    channels.append(snippet["channelTitles"])

        # collaborators フィールドもチェック
        if "collaborators" in snippet:
            if isinstance(snippet["collaborators"], list):
                for collab in snippet["collaborators"]:
                    # collaboratorが辞書でchannelTitleを持つ場合
                    if isinstance(collab, dict) and "channelTitle" in collab:
                        if collab["channelTitle"] not in channels:
                            channels.append(collab["channelTitle"])
                    # collaboratorが文字列の場合
                    elif isinstance(collab, str) and collab not in channels:
                        channels.append(collab)

        # カンマ区切りの文字列に変換
        channel_str = ",".join(channels)

        # 返す辞書を作成
        youtube_res = {
            "view": int(statistics["viewCount"]),
            "like": int(statistics.get("likeCount", statistics.get("favoriteCount", 0))),
            "title": item["snippet"]["title"],
            "channel": channel_str,
            "upload_time": jst_upload_time
        }
        
    except Exception:
        return {}
        
    return youtube_res