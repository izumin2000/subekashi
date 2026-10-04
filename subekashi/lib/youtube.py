from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.settings import YOUTUBE_API_KEY
from datetime import datetime
import json
import pytz


# APIの呼び出しに失敗した（動画が削除・非公開であることとは区別する）
class YoutubeApiError(Exception):
    pass


# クォータ超過・APIキー未設定など、以降の呼び出しも全て失敗し続ける
class YoutubeApiUnavailableError(YoutubeApiError):
    pass


def is_quota_exceeded(error):
    try:
        errors = json.loads(error.content.decode("utf-8"))["error"]["errors"]
        return any(err.get("reason") == "quotaExceeded" for err in errors)
    except (ValueError, KeyError, TypeError, AttributeError):
        return False


# 動画が削除・非公開なら{}を返し、APIの呼び出しに失敗したらYoutubeApiErrorを送出する
def get_youtube_api(video_id):
    # YOUTUBE_API_KEYが空なら
    if YOUTUBE_API_KEY == "":
        raise YoutubeApiUnavailableError("YOUTUBE_API_KEYが設定されていません")

    try:
        # YouTubeからデータを取得
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.videos().list(
            part="snippet,statistics,liveStreamingDetails",
            id=video_id
        )
        response = request.execute()

    # HttpErrorの文字列にはAPIキーを含むURLが入るため、例外のメッセージには含めない
    except HttpError as e:
        if is_quota_exceeded(e):
            raise YoutubeApiUnavailableError("YouTube Data APIのクォータを超過しました") from e
        raise YoutubeApiError(f"YouTube Data APIの呼び出しに失敗しました（HTTP {e.status_code}）") from e
    except Exception as e:
        raise YoutubeApiError("YouTube Data APIの呼び出しに失敗しました") from e

    # 動画が削除・非公開なら
    if not response.get("items"):
        return {}

    try:
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
            "author": item["snippet"]["channelTitle"],
            "upload_time": jst_upload_time
        }
        
    except Exception as e:
        raise YoutubeApiError("YouTube Data APIのレスポンスを解析できませんでした") from e

    return youtube_res