# 全て歌詞の所為です。 MCP サーバー

AI（Claude Desktop・Claude Code など）から「全て歌詞の所為です。」の曲・作者・編集履歴を調べるための、**読み取り専用**の [MCP](https://modelcontextprotocol.io/) サーバーです。サイトの公開 API（[`/llms.txt`](https://lyrics.imicomweb.com/llms.txt) に仕様があります）を呼ぶだけで、Django 側には何も変更を加えていません。

利用者のマシンで動かす stdio 型です。サーバー側に常駐させる形にしていないのは、公開 API の制限（IP ごとに 1 秒に 2 回）が全利用者で共有されてしまうためです。

曲の追加・編集・削除や荒らし報告など、データを書き換えるツールはありません。

## ツール

| ツール | できること |
| --- | --- |
| `search_songs` | 曲の検索。タイトル・作者・歌詞・URL・模倣関係・カテゴリ・メディア・真偽値のフラグ・YouTube の再生回数などで絞り込み、`sort`・`page`・`size` で並べて区切る。歌詞は `include_lyrics=true` のときだけ付く |
| `get_song` | 曲 1 件の詳細。歌詞の全文を含む |
| `get_author` | 作者 1 人の詳細（別名・リンク） |
| `get_song_history` | 曲の編集履歴（新しい順） |

AI が扱いやすいよう、API の応答を次のように変えています。

- 曲の `imitateds`（その曲を模倣している曲の ID の一覧。最大で 1400 件を超える）は、`imitated_count`（件数）にする。一覧が必要なときは `search_songs` の `imitate` にその曲の ID を渡す
- 曲の真偽値は、`True` のものだけを `flags` に並べる
- 編集履歴の `changes` は、1 つの欄が 1000 文字を超えるとき（歌詞を丸ごと入れ替えた編集など）は切り詰め、`…（省略。全N文字）` を付ける
- 作者名からは作者を探せない（API に名前での絞り込みが無い）ため、`search_songs` の `author_exact` で曲を探し、結果の `authors` から ID を得る

## セットアップ

Python 3.10 以上が必要です。

```bash
cd mcp
python -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip install -r requirements.txt
```

### Claude Code

```bash
claude mcp add --transport stdio subekashi -- /path/to/subekashi/mcp/.venv/bin/python /path/to/subekashi/mcp/run.py
```

Windows では `python` に `...\mcp\.venv\Scripts\python.exe` を指定します。

### Claude Desktop

設定ファイル（`claude_desktop_config.json`）の `mcpServers` に追加します。

```json
{
  "mcpServers": {
    "subekashi": {
      "command": "/path/to/subekashi/mcp/.venv/bin/python",
      "args": ["/path/to/subekashi/mcp/run.py"]
    }
  }
}
```

## 環境変数

| 名前 | 既定 | 説明 |
| --- | --- | --- |
| `SUBEKASHI_BASE_URL` | `https://lyrics.imicomweb.com` | 接続先。開発サーバーで試すときは `http://subekashi.localhost:8000` のように指定する（`*.localhost` は OS によって名前解決できないため、`127.0.0.1` に接続して `Host` ヘッダーに元の名前を送る） |

## レート制限

公開 API は IP ごとに 1 秒に 2 回までです。このサーバーは API を呼ぶ間隔を 0.5 秒以上空けます。それでも 429 が返ったときは、`Retry-After` の秒数（最大 10 秒）だけ待って 3 回まで再試行し、それでも通らなければ待つ時間を添えたメッセージを AI に返します。AI が複数のツールを同時に呼んでも、順に間隔を空けて呼びます（6 件を同時に呼ぶと 3 秒ほどかかります）。

## テスト

Django のテスト（`python manage.py test subekashi.tests article.tests`）には含まれません。`mcp/` 側で次のとおり実行します。外部のサイトには接続せず、手元に立てた偽のサイトに対して通信を確かめます。

```bash
cd mcp
.venv/bin/python -m unittest discover -s tests
```

`search_songs` の引数が曲の検索（`SongFilter`）のパラメータと食い違っていないかは、Django のテスト（`subekashi/tests/test_mcp.py`）で確かめています。

## 注意

- `mcp/` に `__init__.py` を置かないでください。リポジトリのルートからの実行時に、同名の `mcp`（SDK）を隠してしまいます
