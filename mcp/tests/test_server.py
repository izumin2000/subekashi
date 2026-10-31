import json
import unittest

from mcp.server.mcpserver.exceptions import ToolError

from subekashi_mcp.client import ApiError
from subekashi_mcp.server import MAX_CHANGE_CELL, create_server


def song(**overrides):
    return {
        "id": 1, "title": "曲", "authors": [{"id": 7, "name": "作者"}], "url": ["https://example.com/1"],
        "imitates": [5], "imitateds": [2, 3, 4], "prush": None, "post_time": "2026-10-31T18:03:49+09:00", "upload_time": None,
        "is_original": False, "is_joke": False, "is_deleted": True, "is_draft": False, "is_inst": False, "is_subeana": True,
        "is_special": False, "is_lock": False, "is_limited": False, "is_questionable": False,
        "view": 0, "like": 0, "category": "song", "lyrics": "一行目\n二行目",
        **overrides,
    }


def page(result, **overrides):
    return {"count": len(result), "page": 1, "size": 20, "max_page": 1, "result": result, **overrides}


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    async def get(self, path, params=None):
        self.calls.append((path, params))
        if self.error:
            raise self.error
        return self.response


class ServerTestBase(unittest.IsolatedAsyncioTestCase):
    async def call(self, client, name, arguments=None):
        result = await create_server(client).call_tool(name, arguments or {})
        self.assertFalse(result.is_error)
        self.assertEqual(len(result.content), 1)
        self.assertIsNone(result.structured_content)
        return json.loads(result.content[0].text)


class ToolListTest(ServerTestBase):
    async def test_has_four_read_only_tools(self):
        tools = await create_server(FakeClient()).list_tools()
        self.assertEqual({tool.name for tool in tools}, {"search_songs", "get_song", "get_author", "get_song_history"})
        for tool in tools:
            with self.subTest(tool=tool.name):
                self.assertTrue(tool.description)
                self.assertTrue(tool.annotations.read_only_hint)
                self.assertFalse(tool.annotations.destructive_hint)

    async def test_search_songs_documents_every_parameter(self):
        tools = {tool.name: tool for tool in await create_server(FakeClient()).list_tools()}
        properties = tools["search_songs"].input_schema["properties"]
        for name, schema in properties.items():
            with self.subTest(parameter=name):
                self.assertTrue(schema.get("description"))
        self.assertEqual(properties["sort"]["default"], "id")
        self.assertIn("random", properties["sort"]["enum"])
        self.assertEqual(properties["size"]["maximum"], 100)


class SearchSongsTest(ServerTestBase):
    async def test_sends_filters_with_paging_defaults(self):
        client = FakeClient(page([song()]))
        await self.call(client, "search_songs", {"author_exact": "作者", "is_joke": False, "imitate": 3})
        path, params = client.calls[0]
        self.assertEqual(path, "/api/song/")
        sent = {name: value for name, value in params.items() if value is not None}
        self.assertEqual(sent, {"author_exact": "作者", "is_joke": False, "imitate": 3, "sort": "id", "page": 1, "size": 20})

    async def test_does_not_send_tool_only_arguments(self):
        client = FakeClient(page([song()]))
        await self.call(client, "search_songs", {"include_lyrics": True})
        _, params = client.calls[0]
        self.assertNotIn("include_lyrics", params)
        self.assertNotIn("client", params)

    async def test_summarizes_songs_without_lyrics(self):
        data = await self.call(FakeClient(page([song()], count=57, max_page=3)), "search_songs")
        self.assertEqual((data["count"], data["page"], data["size"], data["max_page"]), (57, 1, 20, 3))
        self.assertEqual(data["result"], [{
            "id": 1, "title": "曲", "authors": [{"id": 7, "name": "作者"}], "url": ["https://example.com/1"],
            "category": "song", "prush": None, "post_time": "2026-10-31T18:03:49+09:00", "upload_time": None,
            "view": 0, "like": 0, "imitates": [5], "flags": ["is_subeana", "is_deleted"], "imitated_count": 3,
        }])

    async def test_includes_lyrics_on_request(self):
        data = await self.call(FakeClient(page([song()])), "search_songs", {"include_lyrics": True})
        self.assertEqual(data["result"][0]["lyrics"], "一行目\n二行目")

    async def test_imitated_ids_are_replaced_by_a_count(self):
        """最も模倣された曲は1400件を超えるため、idの一覧は返さない"""
        data = await self.call(FakeClient(page([song(imitateds=list(range(1463)))])), "search_songs")
        self.assertEqual(data["result"][0]["imitated_count"], 1463)
        self.assertNotIn("imitateds", data["result"][0])

    async def test_output_is_compact_and_keeps_japanese(self):
        result = await create_server(FakeClient(page([song()]))).call_tool("search_songs", {})
        text = result.content[0].text
        self.assertIn("曲", text)
        self.assertNotIn("\\u", text)
        self.assertNotIn("\n", text)

    async def test_api_error_is_shown_to_the_model(self):
        client = FakeClient(error=ApiError("リクエストが正しくありません: view_gte: 値は1以上である必要があります: -1", 400))
        with self.assertRaises(ToolError) as caught:
            await create_server(client).call_tool("search_songs", {"view_gte": 1})
        self.assertIn("view_gte: 値は1以上である必要があります", str(caught.exception))

    async def test_rate_limit_message_is_shown_to_the_model(self):
        client = FakeClient(error=ApiError("アクセスが多すぎます（IPごとに1秒に2回まで）。1秒ほど待ってから再試行してください。", 429))
        with self.assertRaises(ToolError) as caught:
            await create_server(client).call_tool("search_songs", {})
        self.assertIn("1秒に2回", str(caught.exception))

    async def test_rejects_invalid_arguments(self):
        for arguments in [{"size": 0}, {"size": 101}, {"page": 0}, {"sort": "bogus"}, {"imitate": 0}, {"view_gte": -1}]:
            with self.subTest(arguments=arguments):
                client = FakeClient(page([]))
                with self.assertRaises(ToolError):
                    await create_server(client).call_tool("search_songs", arguments)
                self.assertEqual(client.calls, [])


class GetSongTest(ServerTestBase):
    async def test_returns_song_with_lyrics(self):
        client = FakeClient(song())
        data = await self.call(client, "get_song", {"song_id": 5})
        self.assertEqual(client.calls, [("/api/song/5/", None)])
        self.assertEqual(data["lyrics"], "一行目\n二行目")
        self.assertEqual(data["imitated_count"], 3)
        self.assertNotIn("imitateds", data)

    async def test_not_found_message(self):
        with self.assertRaises(ToolError) as caught:
            await create_server(FakeClient(error=ApiError("見つかりません。", 404))).call_tool("get_song", {"song_id": 5})
        self.assertIn("曲 5 は見つかりません", str(caught.exception))

    async def test_other_errors_pass_through(self):
        client = FakeClient(error=ApiError("サイトがエラーを返しました（HTTP 500）。しばらくしてから再試行してください。", 500))
        with self.assertRaises(ToolError) as caught:
            await create_server(client).call_tool("get_song", {"song_id": 5})
        self.assertIn("HTTP 500", str(caught.exception))

    async def test_rejects_invalid_id(self):
        for song_id in [0, -1, 2147483648]:
            with self.subTest(song_id=song_id):
                with self.assertRaises(ToolError):
                    await create_server(FakeClient(song())).call_tool("get_song", {"song_id": song_id})


class GetAuthorTest(ServerTestBase):
    async def test_returns_author(self):
        author = {"id": 1, "name": "作者", "aliases": [{"name": "略称", "alias_type": "abbr"}], "links": ["https://example.com/a"]}
        client = FakeClient(author)
        self.assertEqual(await self.call(client, "get_author", {"author_id": 1}), author)
        self.assertEqual(client.calls, [("/api/author/1/", None)])

    async def test_not_found_message(self):
        with self.assertRaises(ToolError) as caught:
            await create_server(FakeClient(error=ApiError("見つかりません。", 404))).call_tool("get_author", {"author_id": 9})
        self.assertIn("作者 9 は見つかりません", str(caught.exception))


class GetSongHistoryTest(ServerTestBase):
    def history(self, changes):
        return {"id": 10, "song": 5, "author": None, "title": "編集", "history_type": "edit", "create_time": "2026-10-31T18:06:24+09:00", "changes": changes, "editor": 1}

    async def test_sends_song_and_paging(self):
        client = FakeClient(page([self.history([["種類", "編集前", "編集後"], ["カテゴリ", "曲", "アレンジ"]])]))
        data = await self.call(client, "get_song_history", {"song_id": 5, "page": 2})
        self.assertEqual(client.calls, [("/api/history/", {"song": 5, "page": 2, "size": 10})])
        self.assertEqual(data["result"][0]["changes"], [["種類", "編集前", "編集後"], ["カテゴリ", "曲", "アレンジ"]])
        self.assertEqual(data["count"], 1)

    async def test_long_cells_are_truncated_with_the_original_length(self):
        lyrics = "あ" * (MAX_CHANGE_CELL + 500)
        data = await self.call(FakeClient(page([self.history([["種類", "編集前", "編集後"], ["歌詞", "短い", lyrics]])])), "get_song_history", {"song_id": 5})
        row = data["result"][0]["changes"][1]
        self.assertEqual(row[1], "短い")
        self.assertTrue(row[2].startswith("あ" * MAX_CHANGE_CELL + "…"))
        self.assertIn(f"全{len(lyrics)}文字", row[2])
        self.assertLess(len(row[2]), len(lyrics))

    async def test_cell_at_the_limit_is_kept(self):
        cell = "あ" * MAX_CHANGE_CELL
        data = await self.call(FakeClient(page([self.history([["種類", "編集前", "編集後"], ["歌詞", "", cell]])])), "get_song_history", {"song_id": 5})
        self.assertEqual(data["result"][0]["changes"][1][2], cell)

    async def test_history_without_changes_is_kept(self):
        data = await self.call(FakeClient(page([self.history(None)])), "get_song_history", {"song_id": 5})
        self.assertIsNone(data["result"][0]["changes"])

    async def test_rejects_invalid_size(self):
        for size in [0, 51]:
            with self.subTest(size=size):
                with self.assertRaises(ToolError):
                    await create_server(FakeClient(page([]))).call_tool("get_song_history", {"song_id": 5, "size": size})
