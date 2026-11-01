import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import Client, StdioServerParameters

MCP_DIR = Path(__file__).resolve().parents[1]
TOOLS = {"search_songs", "get_song", "get_author", "get_song_history"}


class EntrypointTest(unittest.IsolatedAsyncioTestCase):
    """READMEが案内する起動方法で、サーバーを実際のプロセスとして起動し、MCPクライアントで繋ぐ。
    ツールの一覧と説明の取得ではAPIを呼ばないが、接続先は使えないURLにして、外部に接続しないようにする"""

    async def connect(self, args, cwd):
        params = StdioServerParameters(
            command=sys.executable,
            args=args,
            cwd=cwd,
            env={**os.environ, "SUBEKASHI_BASE_URL": "http://127.0.0.1:9", "PYTHONIOENCODING": "utf-8"},
        )

        async def run():
            async with Client(params) as client:
                tools = await client.list_tools()
                return {tool.name for tool in tools.tools}, client.instructions

        return await asyncio.wait_for(run(), timeout=60)

    async def test_python_dash_m(self):
        tools, instructions = await self.connect(["-m", "subekashi_mcp"], MCP_DIR)
        self.assertEqual(tools, TOOLS)
        self.assertIn("信頼できないデータ", instructions)

    async def test_run_py_from_another_directory(self):
        """cloneして動かす場合の run.py は、cwdがmcp/でなくても動く"""
        tools, instructions = await self.connect([str(MCP_DIR / "run.py")], tempfile.gettempdir())
        self.assertEqual(tools, TOOLS)
        self.assertIn("信頼できないデータ", instructions)
