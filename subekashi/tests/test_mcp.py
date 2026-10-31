"""
MCPサーバー（mcp/）が公開APIの仕様と食い違っていないかのテスト

mcp/はDjangoとは独立した、別の依存を持つプロジェクトのため、SDKをimportせずソースをastで読んで確かめる。
mcp/自体のテストは mcp/tests/ にあり、mcp/ で `python -m unittest discover -s tests` として実行する。
"""
import ast
from pathlib import Path
from django.test import TestCase
from subekashi.lib.song_filterset import SongFilter
from subekashi.lib.song_search import song_search


MCP_SERVER = Path(__file__).resolve().parents[2] / "mcp" / "subekashi_mcp" / "server.py"
# 検索結果の形を変える、MCPサーバーだけの引数
MCP_ONLY_PARAMS = {"include_lyrics"}


class McpServerSourceTest(TestCase):
    def setUp(self):
        self.tree = ast.parse(MCP_SERVER.read_text(encoding="utf-8"))

    def _function_params(self, name):
        function = next(node for node in ast.walk(self.tree) if isinstance(node, ast.AsyncFunctionDef) and node.name == name)
        return {arg.arg for arg in function.args.args}

    def _literal_values(self, name):
        assign = next(node for node in self.tree.body if isinstance(node, ast.Assign) and node.targets[0].id == name)
        return [element.value for element in assign.value.slice.elts]

    def test_search_songs_sends_exactly_the_song_filter_params(self):
        """search_songsがAPIに送る名前は、曲の検索（SongFilter）のパラメータと page・size に過不足なく一致する（#1311）。
        送る名前は、引数からMCPサーバーだけの引数を除いたもの（mcp/tests/test_server.py が、実際に送る名前がそれと一致することを確かめる）"""
        sent = self._function_params("search_songs") - MCP_ONLY_PARAMS
        self.assertEqual(sent, set(SongFilter.base_filters) | {"page", "size"})

    def test_sort_choices_are_accepted_by_the_api(self):
        """search_songsのsortの選択肢は、すべて曲のAPIが受け付ける（#1311）"""
        values = self._literal_values("SongSort")
        self.assertIn("random", values)
        for value in values:
            with self.subTest(sort=value):
                song_search({"sort": value})
