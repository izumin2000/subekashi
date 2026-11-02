import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, StdioServerParameters

MCP_DIR = Path(__file__).resolve().parents[1]
TOOLS = {"search_songs", "get_song", "get_author", "get_song_history"}
# パッケージとしてインストールしたコマンド（CIでは subekashi-mcp）。指定したときだけ、そのコマンドを起動するテストを実行する
INSTALLED_COMMAND = os.environ.get("SUBEKASHI_MCP_COMMAND")


class EntrypointTest(unittest.IsolatedAsyncioTestCase):
    """READMEが案内する起動方法で、サーバーを実際のプロセスとして起動し、MCPクライアントで繋ぐ。
    ツールの一覧と説明の取得ではAPIを呼ばないが、接続先は使えないURLにして、外部に接続しないようにする"""

    async def connect(self, command, args, cwd):
        params = StdioServerParameters(
            command=command,
            args=args,
            cwd=cwd,
            env={**os.environ, "SUBEKASHI_BASE_URL": "http://127.0.0.1:9", "PYTHONIOENCODING": "utf-8"},
        )

        async def run():
            async with Client(params) as client:
                tools = await client.list_tools()
                return {tool.name for tool in tools.tools}, client.instructions

        return await asyncio.wait_for(run(), timeout=60)

    def assert_server(self, tools, instructions):
        self.assertEqual(tools, TOOLS)
        self.assertIn("信頼できないデータ", instructions)

    async def test_python_dash_m(self):
        self.assert_server(*await self.connect(sys.executable, ["-m", "subekashi_mcp"], MCP_DIR))

    async def test_run_py_from_another_directory(self):
        """cloneして動かす場合の run.py は、cwdがmcp/でなくても動く"""
        self.assert_server(*await self.connect(sys.executable, [str(MCP_DIR / "run.py")], tempfile.gettempdir()))

    @unittest.skipUnless(INSTALLED_COMMAND, "SUBEKASHI_MCP_COMMANDにインストールしたコマンドを指定したときだけ実行する")
    async def test_installed_command(self):
        """パッケージとしてインストールしたコマンド（uv tool install・uvxで起動されるもの）を、ソースツリーの外から起動する。
        packagesの足し忘れなど、インストールした環境でだけ起きる問題に気づくためのテスト。
        標準入力へ1行だけ送って閉じる方法は、応答を書く前に終了する競合があるため、MCPクライアントで繋ぐ"""
        self.assert_server(*await self.connect(INSTALLED_COMMAND, [], tempfile.gettempdir()))
