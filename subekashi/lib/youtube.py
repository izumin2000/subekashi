from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config.settings import YOUTUBE_API_KEY
from datetime import datetime
import json
import pytz


# APIの呼び出しに失敗した（動画が削除・非公開であることとは区別する）
class YoutubeApiError(Exception):
    pass


# クォータ超過・APIキーの問題など、以降の呼び出しも全て失敗し続ける
class YoutubeApiUnavailableError(YoutubeApiError):
    pass


# 日付が変わるまで回復しないクォータ超過の理由
# rateLimitExceededは短時間で回復するため含めない
QUOTA_EXCEEDED_REASONS = {"quotaExceeded", "dailyLimitExceeded"}

# APIキーが無効・失効している、APIが有効になっていないなど、設定を直すまで回復しない理由
# API_KEY_INVALID・API_KEY_SERVICE_BLOCKEDなど「API_KEY_」から始まる理由も含める
CONFIG_ERROR_REASONS = {"keyInvalid", "keyExpired", "accessNotConfigured", "SERVICE_DISABLED"}


# エラーレスポンスのerrors・detailsに含まれる理由の一覧を返す
def get_error_reasons(error):
    try:
        data = json.loads(error.content.decode("utf-8"))["error"]
        details = data.get("errors", []) + data.get("details", [])
        return [detail["reason"] for detail in details if isinstance(detail, dict) and isinstance(detail.get("reason"), str)]
    except (ValueError, KeyError, TypeError, AttributeError):
        return []


# 動画が削除・非公開なら{}を返し、APIの呼び出しに失敗したらYoutubeApiErrorを送出する
# 元の例外の文字列にはAPIキーを含むURLが入り、トレースバックにも出力されるため、
# 例外は連鎖させず（from None）、メッセージにはAPIキーを含まない情報のみを入れる
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

    except HttpError as e:
        reasons = get_error_reasons(e)
        detail = " ".join([f"HTTP {e.status_code}", *reasons])
        if any(reason in QUOTA_EXCEEDED_REASONS for reason in reasons):
            raise YoutubeApiUnavailableError(f"YouTube Data APIのクォータを超過しました（{detail}）") from None
        if any(reason in CONFIG_ERROR_REASONS or reason.startswith("API_KEY_") for reason in reasons):
            raise YoutubeApiUnavailableError(f"YouTube Data APIのAPIキーまたは設定に問題があります（{detail}）") from None
        raise YoutubeApiError(f"YouTube Data APIの呼び出しに失敗しました（{detail}）") from None
    except Exception as e:
        raise YoutubeApiError(f"YouTube Data APIの呼び出しに失敗しました（{type(e).__name__}）") from None

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
        raise YoutubeApiError(f"YouTube Data APIのレスポンスを解析できませんでした（{type(e).__name__}）") from None

    return youtube_res
