from googleapiclient.discovery import build
from config.settings import YOUTUBE_API_KEY
from datetime import datetime
from time import sleep


def get_youtube_api(video_id):
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
        yt_res["title"] = item["snippet"]["title"]
        yt_res["channel"] = item["snippet"]["channelTitle"]
        upload_time = item["snippet"]["publishedAt"]
        upload_time = datetime.strptime(upload_time, "%Y-%m-%dT%H:%M:%SZ")
        yt_res["upload_time"] = upload_time
        
    except Exception:
        pass
        
    return yt_res