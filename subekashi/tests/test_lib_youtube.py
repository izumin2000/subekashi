"""
lib/youtube.py のテスト（YouTube Data APIはモック化、#1146）

get_youtube_api: 動画の情報の取得と、「動画が存在しない（削除・非公開）」場合と「APIの呼び出しに失敗した」場合を
区別して扱うこと（前者は{}を返し、後者はYoutubeApiErrorを送出する）を検証する。
クォータ超過・APIキーの問題（未設定・無効・失効など）は以降の呼び出しも全て失敗するため、YoutubeApiUnavailableErrorを
送出することを検証する。また、元の例外の文字列にはAPIキーが入るため、例外を連鎖させないことを検証する。
"""
import json
import socket
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz
from django.test import SimpleTestCase
from googleapiclient.errors import HttpError

from subekashi.lib.youtube import YoutubeApiError, YoutubeApiUnavailableError, get_youtube_api


def make_item(**snippet_overrides):
    snippet = {
        "title": "テスト動画",
        "channelTitle": "テストチャンネル",
        "publishedAt": "2024-01-01T00:00:00Z",
        "liveBroadcastContent": "none",
    }
    snippet.update(snippet_overrides)
    return {
        "snippet": snippet,
        "statistics": {"viewCount": "1000", "likeCount": "100"},
    }


def make_http_error(status, reasons, detail_reasons=()):
    content = {
        "error": {
            "code": status,
            "message": "error",
            "errors": [{"reason": reason} for reason in reasons],
            "details": [{"@type": "type.googleapis.com/google.rpc.ErrorInfo", "reason": reason} for reason in detail_reasons],
        }
    }
    return HttpError(
        MagicMock(status=status, reason="error"),
        json.dumps(content).encode("utf-8"),
        uri="https://youtube.googleapis.com/youtube/v3/videos?id=aaaaaaaaaaa&key=dummy-key",
    )


@patch("subekashi.lib.youtube.YOUTUBE_API_KEY", "dummy-key")
@patch("subekashi.lib.youtube.build")
class GetYoutubeApiTest(SimpleTestCase):
    def set_response(self, mock_build, response=None, error=None):
        execute = mock_build.return_value.videos.return_value.list.return_value.execute
        if error:
            execute.side_effect = error
        else:
            execute.return_value = response

    def test_returns_video_info(self, mock_build):
        self.set_response(mock_build, {"items": [make_item()]})
        res = get_youtube_api("aaaaaaaaaaa")

        self.assertEqual(res["view"], 1000)
        self.assertEqual(res["like"], 100)
        self.assertEqual(res["title"], "テスト動画")
        self.assertEqual(res["author"], "テストチャンネル")
        # 日本標準時に変換される
        self.assertEqual(res["upload_time"], pytz.timezone("Asia/Tokyo").localize(datetime(2024, 1, 1, 9, 0)))

    def test_upcoming_video_uses_scheduled_publish_time(self, mock_build):
        item = make_item(liveBroadcastContent="upcoming", scheduledPublishTime="2024-02-01T12:00:00Z")
        self.set_response(mock_build, {"items": [item]})
        res = get_youtube_api("aaaaaaaaaaa")

        self.assertEqual(res["upload_time"], pytz.timezone("Asia/Tokyo").localize(datetime(2024, 2, 1, 21, 0)))

    def test_hidden_like_count_returns_zero(self, mock_build):
        item = make_item()
        del item["statistics"]["likeCount"]
        self.set_response(mock_build, {"items": [item]})

        self.assertEqual(get_youtube_api("aaaaaaaaaaa")["like"], 0)

    def test_deleted_or_private_video_returns_empty_dict(self, mock_build):
        # 削除・非公開の動画はitemsが空になる
        self.set_response(mock_build, {"items": []})

        self.assertEqual(get_youtube_api("aaaaaaaaaaa"), {})

    def test_quota_exceeded_raises_unavailable_error(self, mock_build):
        for reason in ["quotaExceeded", "dailyLimitExceeded"]:
            with self.subTest(reason=reason):
                self.set_response(mock_build, error=make_http_error(403, [reason]))

                with self.assertRaises(YoutubeApiUnavailableError) as cm:
                    get_youtube_api("aaaaaaaaaaa")
                self.assertIn("クォータを超過しました", str(cm.exception))
                self.assertIn(reason, str(cm.exception))

    def test_api_key_or_config_error_raises_unavailable_error(self, mock_build):
        # APIキーが無効・失効している、APIが有効になっていないなど、設定を直すまで回復しないエラー
        cases = [
            (400, ["keyInvalid"], []),
            (400, ["keyExpired"], []),
            (400, ["badRequest"], ["API_KEY_INVALID"]),
            (403, ["forbidden"], ["API_KEY_SERVICE_BLOCKED"]),
            (403, ["accessNotConfigured"], ["SERVICE_DISABLED"]),
        ]
        for status, reasons, detail_reasons in cases:
            with self.subTest(reasons=reasons, detail_reasons=detail_reasons):
                self.set_response(mock_build, error=make_http_error(status, reasons, detail_reasons))

                with self.assertRaises(YoutubeApiUnavailableError) as cm:
                    get_youtube_api("aaaaaaaaaaa")
                self.assertIn("APIキーまたは設定に問題があります", str(cm.exception))

    def test_rate_limit_exceeded_raises_api_error(self, mock_build):
        # 短時間で回復するため、処理を打ち切るYoutubeApiUnavailableErrorにはしない
        self.set_response(mock_build, error=make_http_error(403, ["rateLimitExceeded"]))

        with self.assertRaises(YoutubeApiError) as cm:
            get_youtube_api("aaaaaaaaaaa")
        self.assertNotIsInstance(cm.exception, YoutubeApiUnavailableError)
        self.assertIn("rateLimitExceeded", str(cm.exception))

    def test_other_forbidden_error_raises_api_error(self, mock_build):
        self.set_response(mock_build, error=make_http_error(403, ["forbidden"]))

        with self.assertRaises(YoutubeApiError) as cm:
            get_youtube_api("aaaaaaaaaaa")
        self.assertNotIsInstance(cm.exception, YoutubeApiUnavailableError)

    def test_server_error_raises_api_error(self, mock_build):
        self.set_response(mock_build, error=make_http_error(500, ["backendError"]))

        with self.assertRaises(YoutubeApiError) as cm:
            get_youtube_api("aaaaaaaaaaa")
        self.assertNotIsInstance(cm.exception, YoutubeApiUnavailableError)

    def test_unexpected_error_response_raises_api_error(self, mock_build):
        # エラーレスポンスの形式が想定外でも、YoutubeApiError以外の例外を送出しない
        contents = [
            {"error": "error"},
            {"error": {"errors": "error"}},
            {"error": {"errors": ["error", {"reason": 403}], "details": [{"reason": None}]}},
        ]
        for content in contents:
            with self.subTest(content=content):
                error = HttpError(MagicMock(status=403, reason="error"), json.dumps(content).encode("utf-8"))
                self.set_response(mock_build, error=error)

                with self.assertRaises(YoutubeApiError) as cm:
                    get_youtube_api("aaaaaaaaaaa")
                self.assertNotIsInstance(cm.exception, YoutubeApiUnavailableError)

    def test_non_json_http_error_raises_api_error(self, mock_build):
        self.set_response(mock_build, error=HttpError(MagicMock(status=502, reason="Bad Gateway"), b"<html>Bad Gateway</html>"))

        with self.assertRaises(YoutubeApiError) as cm:
            get_youtube_api("aaaaaaaaaaa")
        self.assertNotIsInstance(cm.exception, YoutubeApiUnavailableError)

    def test_network_error_raises_api_error(self, mock_build):
        error = socket.timeout("timed out")
        self.set_response(mock_build, error=error)

        with self.assertRaises(YoutubeApiError) as cm:
            get_youtube_api("aaaaaaaaaaa")
        self.assertNotIsInstance(cm.exception, YoutubeApiUnavailableError)
        # 調査しやすいよう、元の例外のクラス名をメッセージに含める
        self.assertIn(type(error).__name__, str(cm.exception))

    def test_unexpected_response_raises_api_error(self, mock_build):
        # 動画は存在するため、削除・非公開として{}を返してはいけない
        item = make_item()
        del item["statistics"]
        self.set_response(mock_build, {"items": [item]})

        with self.assertRaises(YoutubeApiError) as cm:
            get_youtube_api("aaaaaaaaaaa")
        self.assertIn("KeyError", str(cm.exception))

    def test_error_does_not_expose_api_key(self, mock_build):
        # エラーメッセージはDiscordの公開チャンネルに通知されるため、APIキーを含むURLを含めない。
        # また、元のHttpErrorの文字列にはAPIキーが入り、連鎖させるとトレースバックに出力されるため、連鎖させない
        for reasons in [["quotaExceeded"], ["keyInvalid"], ["forbidden"]]:
            with self.subTest(reasons=reasons):
                self.set_response(mock_build, error=make_http_error(403, reasons))

                with self.assertRaises(YoutubeApiError) as cm:
                    get_youtube_api("aaaaaaaaaaa")
                self.assertNotIn("dummy-key", str(cm.exception))
                self.assertIsNone(cm.exception.__cause__)
                self.assertTrue(cm.exception.__suppress_context__)

    def test_empty_api_key_raises_unavailable_error(self, mock_build):
        with patch("subekashi.lib.youtube.YOUTUBE_API_KEY", ""):
            with self.assertRaises(YoutubeApiUnavailableError):
                get_youtube_api("aaaaaaaaaaa")
        mock_build.assert_not_called()
