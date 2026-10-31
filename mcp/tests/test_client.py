import asyncio
import json
import os
import threading
import time
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

from subekashi_mcp.client import BASE_URL_ENV, DEFAULT_BASE_URL, MAX_RETRY_WAIT, ApiError, Client, _retry_after


class FakeSite:
    """決めた応答を順に返すHTTPサーバー。最後の応答は繰り返す"""

    def __init__(self):
        self.requests = []
        self.responses = [(200, {}, b"{}")]
        site = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                site.requests.append({"path": self.path, "headers": dict(self.headers)})
                index = min(len(site.requests), len(site.responses)) - 1
                status, headers, body = site.responses[index]
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        # 既定の0.5秒間隔だと、shutdown()がテストごとに最大0.5秒待たされる
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    def respond(self, *responses):
        self.responses = list(responses)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def json_response(data, status=200, headers=None):
    return status, headers or {}, json.dumps(data).encode()


class ClientTestBase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # 環境にプロキシの設定があっても、手元の偽サイトには直接つなぐ
        patcher = patch.dict(os.environ, {"no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.site = FakeSite()
        self.site.start()
        self.addCleanup(self.site.stop)

    def client(self, **kwargs):
        kwargs.setdefault("min_interval", 0)
        return Client(self.site.url, **kwargs)


class ClientRequestTest(ClientTestBase):
    async def test_returns_parsed_json(self):
        self.site.respond(json_response({"count": 1, "result": [{"id": 1}]}))
        self.assertEqual(await self.client().get("/api/song/"), {"count": 1, "result": [{"id": 1}]})

    async def test_query_encodes_japanese_and_booleans_and_drops_none(self):
        """日本語はURLエンコードし、真偽値はtrue/falseにして、Noneの引数は送らない"""
        await self.client().get("/api/song/", {"author_exact": "全てあなたの所為です。", "is_joke": False, "is_deleted": True, "title": None, "page": 2})
        path = self.site.requests[0]["path"]
        self.assertEqual(path.split("?")[0], "/api/song/")
        query = dict(pair.split("=") for pair in path.split("?")[1].split("&"))
        self.assertEqual(query, {
            "author_exact": "%E5%85%A8%E3%81%A6%E3%81%82%E3%81%AA%E3%81%9F%E3%81%AE%E6%89%80%E7%82%BA%E3%81%A7%E3%81%99%E3%80%82",
            "is_joke": "false",
            "is_deleted": "true",
            "page": "2",
        })

    async def test_no_query_when_no_params(self):
        await self.client().get("/api/song/1/")
        self.assertEqual(self.site.requests[0]["path"], "/api/song/1/")

    async def test_sends_user_agent_and_accept(self):
        await self.client().get("/api/song/")
        headers = self.site.requests[0]["headers"]
        self.assertTrue(headers["User-Agent"].startswith("subekashi-mcp/"))
        self.assertEqual(headers["Accept"], "application/json")

    async def test_localhost_name_connects_to_loopback_with_host_header(self):
        """subekashi.localhost はOSによって名前解決できないため、127.0.0.1につなぎHostヘッダーに元の名前を送る"""
        client = Client(f"http://subekashi.localhost:{self.site.port}", min_interval=0)
        await client.get("/api/song/")
        self.assertEqual(self.site.requests[0]["headers"]["Host"], f"subekashi.localhost:{self.site.port}")


class ClientErrorTest(ClientTestBase):
    async def test_bad_request_carries_the_error_message(self):
        self.site.respond(json_response({"error": "view_gte: 値は1以上である必要があります: -1"}, 400))
        with self.assertRaises(ApiError) as caught:
            await self.client().get("/api/song/")
        self.assertEqual(caught.exception.status, 400)
        self.assertIn("view_gte: 値は1以上である必要があります: -1", str(caught.exception))

    async def test_not_found(self):
        self.site.respond(json_response({"detail": "No Song matches the given query."}, 404))
        with self.assertRaises(ApiError) as caught:
            await self.client().get("/api/song/99999/")
        self.assertEqual(caught.exception.status, 404)

    async def test_server_error(self):
        self.site.respond((500, {}, b"<h1>Server Error</h1>"))
        with self.assertRaises(ApiError) as caught:
            await self.client().get("/api/song/")
        self.assertEqual(caught.exception.status, 500)
        self.assertIn("HTTP 500", str(caught.exception))

    async def test_success_but_not_json(self):
        self.site.respond((200, {}, b"<html></html>"))
        with self.assertRaises(ApiError) as caught:
            await self.client().get("/api/song/")
        self.assertIn("JSONではありません", str(caught.exception))

    # Windowsでは閉じたポートへの接続の失敗に約2.5秒かかるため、urlopenの失敗を差し替えて確かめる
    async def test_cannot_connect(self):
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(ConnectionRefusedError("refused"))):
            with self.assertRaises(ApiError) as caught:
                await self.client().get("/api/song/")
        self.assertIsNone(caught.exception.status)
        self.assertIn("接続できませんでした", str(caught.exception))
        self.assertIn(self.site.url, str(caught.exception))

    async def test_timeout(self):
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            with self.assertRaises(ApiError) as caught:
                await self.client().get("/api/song/")
        self.assertIsNone(caught.exception.status)
        self.assertIn("接続できませんでした", str(caught.exception))


class ClientRateLimitTest(ClientTestBase):
    async def test_retries_after_429_and_succeeds(self):
        self.site.respond(
            json_response({"detail": "throttled"}, 429, {"Retry-After": "0"}),
            json_response({"detail": "throttled"}, 429, {"Retry-After": "0"}),
            json_response({"count": 1}),
        )
        self.assertEqual(await self.client().get("/api/song/"), {"count": 1})
        self.assertEqual(len(self.site.requests), 3)

    async def test_gives_up_after_max_retries(self):
        self.site.respond(json_response({"detail": "throttled"}, 429, {"Retry-After": "0"}))
        with self.assertRaises(ApiError) as caught:
            await self.client(max_retries=2).get("/api/song/")
        self.assertEqual(caught.exception.status, 429)
        self.assertIn("1秒に2回", str(caught.exception))
        self.assertEqual(len(self.site.requests), 3)

    async def test_waits_for_retry_after(self):
        self.site.respond(json_response({"detail": "throttled"}, 429, {"Retry-After": "0.3"}), json_response({}))
        started = time.monotonic()
        await self.client().get("/api/song/")
        self.assertGreaterEqual(time.monotonic() - started, 0.3)

    async def test_spaces_requests_by_min_interval(self):
        client = self.client(min_interval=0.2)
        started = time.monotonic()
        for _ in range(3):
            await client.get("/api/song/")
        self.assertGreaterEqual(time.monotonic() - started, 0.4)

    async def test_spaces_concurrent_requests(self):
        """AIが並行してツールを呼んでも、1秒に2回を超えないよう間隔を空ける"""
        client = self.client(min_interval=0.2)
        started = time.monotonic()
        await asyncio.gather(*[client.get("/api/song/") for _ in range(3)])
        self.assertGreaterEqual(time.monotonic() - started, 0.4)
        self.assertEqual(len(self.site.requests), 3)


class RetryAfterTest(unittest.TestCase):
    def test_uses_header_value(self):
        self.assertEqual(_retry_after({"Retry-After": "3"}), 3)

    def test_defaults_to_one_second(self):
        self.assertEqual(_retry_after({}), 1)
        self.assertEqual(_retry_after({"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}), 1)

    def test_is_capped(self):
        self.assertEqual(_retry_after({"Retry-After": "100"}), MAX_RETRY_WAIT)
        self.assertEqual(_retry_after({"Retry-After": "-5"}), 0)


class ClientBaseUrlTest(unittest.TestCase):
    def test_default_is_production(self):
        with patch.dict(os.environ, clear=True):
            self.assertEqual(Client().base_url, DEFAULT_BASE_URL)

    def test_reads_environment_variable(self):
        with patch.dict(os.environ, {BASE_URL_ENV: "http://subekashi.localhost:8000/"}):
            self.assertEqual(Client().base_url, "http://subekashi.localhost:8000")

    def test_argument_takes_priority_over_environment(self):
        with patch.dict(os.environ, {BASE_URL_ENV: "http://example.com"}):
            self.assertEqual(Client("https://example.org").base_url, "https://example.org")

    def test_rejects_other_schemes(self):
        for url in ["file:///etc/passwd", "ftp://example.com", "example.com", "http://"]:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    Client(url)
