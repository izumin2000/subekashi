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
        
        # 返す辞書を作成
        youtube_res = {
            "view": int(statistics["viewCount"]),
            "like": int(statistics.get("likeCount", statistics.get("favoriteCount", 0))),
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "upload_time": jst_upload_time
        }
        
    except Exception as e:
        print(f'\033[31m{e}\033[0m')
        return {}
        
    return youtube_res