import asyncio
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from . import __version__

BASE_URL_ENV = "SUBEKASHI_BASE_URL"
DEFAULT_BASE_URL = "https://lyrics.imicomweb.com"

# 公開APIはIPごとに1秒に2回まで。間隔を空けて呼び、それでも429が返ったら待って再試行する
MIN_INTERVAL = 0.5
MAX_RETRIES = 3
MAX_RETRY_WAIT = 10
TIMEOUT = 30


# AIに伝える文を持つ、APIの呼び出しの失敗。statusはサイトに接続できなかったときNone
class ApiError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _format_param(value):
    return str(value).lower() if isinstance(value, bool) else value


def _retry_after(headers):
    try:
        wait = float(headers.get("Retry-After", 1))
    except ValueError:
        wait = 1
    return min(max(wait, 0), MAX_RETRY_WAIT)


class Client:
    def __init__(self, base_url=None, min_interval=MIN_INTERVAL, max_retries=MAX_RETRIES, timeout=TIMEOUT):
        base_url = (base_url or os.environ.get(BASE_URL_ENV) or DEFAULT_BASE_URL).rstrip("/")
        parts = urllib.parse.urlsplit(base_url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError(f"{BASE_URL_ENV}はhttp://またはhttps://で始まるURLにしてください: {base_url}")
        self.base_url = base_url
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.timeout = timeout
        self._headers = {"Accept": "application/json", "User-Agent": f"subekashi-mcp/{__version__}"}
        # 開発サーバーの subekashi.localhost はOSによっては名前解決できないため、127.0.0.1に接続しHostヘッダーで元の名前を送る
        if parts.hostname.endswith(".localhost"):
            self._headers["Host"] = parts.netloc
            port = f":{parts.port}" if parts.port else ""
            parts = parts._replace(netloc=f"127.0.0.1{port}")
        self._origin = urllib.parse.urlunsplit(parts).rstrip("/")
        self._next_at = 0.0

    async def get(self, path, params=None):
        query = urllib.parse.urlencode({key: _format_param(value) for key, value in (params or {}).items() if value is not None})
        url = f"{self._origin}{path}" + (f"?{query}" if query else "")
        for attempt in range(self.max_retries + 1):
            await self._wait_turn()
            status, headers, body = await asyncio.to_thread(self._fetch, url)
            if status != 429:
                return self._parse(status, body)
            wait = _retry_after(headers)
            # 並行して呼ばれた他のリクエストも、待つ時間が過ぎるまで送らない
            self._next_at = max(self._next_at, time.monotonic() + wait)
        raise ApiError(f"アクセスが多すぎます（IPごとに1秒に2回まで）。{wait:g}秒ほど待ってから再試行してください。", 429)

    async def _wait_turn(self):
        now = time.monotonic()
        start = max(now, self._next_at)
        self._next_at = start + self.min_interval
        if start > now:
            await asyncio.sleep(start - now)

    def _fetch(self, url):
        request = urllib.request.Request(url, headers=self._headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.headers, e.read()
        except OSError as e:
            raise ApiError(f"サイトに接続できませんでした（{self.base_url}）: {e}") from e

    def _parse(self, status, body):
        try:
            data = json.loads(body)
        except ValueError:
            data = None
        if status == 200:
            if data is None:
                raise ApiError("サイトの応答を読み取れませんでした（JSONではありません）。", status)
            return data
        if status == 400 and isinstance(data, dict):
            raise ApiError(f"リクエストが正しくありません: {data.get('error') or data.get('detail')}", status)
        if status == 404:
            raise ApiError("見つかりません。", status)
        raise ApiError(f"サイトがエラーを返しました（HTTP {status}）。しばらくしてから再試行してください。", status)
