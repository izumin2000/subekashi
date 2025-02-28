from googleapiclient.discovery import build
from config.settings import YOUTUBE_API_KEY
from datetime import datetime
import pytz

def get_youtube_api(video_id):
    try:
        # YouTubeからデータを取得
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.videos().list(
            part="snippet,statistics",
            id=video_id
        )
        response = request.execute()
        
        item = response["items"][0]
        statistics = item["statistics"]
        
        # 日本標準時の投稿日時を取得
        upload_time = datetime.strptime(item["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")

        utc_zone = pytz.utc
        jst_zone = pytz.timezone("Asia/Tokyo")
        jst_upload_time = utc_zone.localize(upload_time).astimezone(jst_zone)
        
        # 返す辞書を作成
        yt_res = {
            "view": int(statistics["viewCount"]),
            "like": int(statistics["likeCount" if ("likeCount" in statistics) else "favoriteCount"]),
            "title": item["snippet"]["title"],
            "channel": item["snippet"]["channelTitle"],
            "upload_time": jst_upload_time
        }
        
    except Exception:
        return {}
        
    return yt_res