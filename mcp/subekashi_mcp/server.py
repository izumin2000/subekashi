import json
from functools import partial
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from . import __version__
from .client import ApiError, Client

INSTRUCTIONS = """「全て歌詞の所為です。」（https://lyrics.imicomweb.com）は、界隈曲と呼ばれる音楽ジャンルの曲を集めたデータベースです。曲のタイトル・歌詞・作者・動画のURL・模倣関係・編集履歴を調べられます。読み取り専用で、曲の追加や編集はできません。

- 作者名から曲を探すときは search_songs の author_exact を使います。作者のidは結果の authors から得られ、get_author で別名やリンクを調べられます
- 模倣関係: imitates は、その曲が模倣している曲（模倣元）のidです。imitated_count は、その曲を模倣している曲（模倣曲）の数で、一覧は search_songs の imitate にその曲のidを渡して得ます
- 何も絞り込まないと、動画が非公開・削除済みの曲（is_deleted）も含めた全曲が対象です
- サイトのAPIにはIPごとに1秒に2回までの制限があるため、続けて呼ぶと待たされることがあります"""

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=True)

# 曲のAPIが返す真偽値のうち、検索結果ではTrueのものだけを flags に並べる
SONG_FLAGS = (
    "is_subeana", "is_original", "is_joke", "is_inst", "is_draft",
    "is_deleted", "is_limited", "is_questionable", "is_special", "is_lock",
)
SONG_KEYS = (
    "id", "title", "authors", "url", "category", "prush", "post_time", "upload_time", "view", "like", "imitates",
)

# 編集履歴の変更内容は、歌詞を丸ごと入れ替えると2万文字を超えることがあるため、長い欄は切り詰める
MAX_CHANGE_CELL = 1000

SongSort = Literal[
    "id", "-id", "title", "-title", "author", "-author", "post_time", "-post_time",
    "upload_time", "-upload_time", "view", "-view", "like", "-like",
    "imitate_count", "-imitate_count", "imitated_count", "-imitated_count", "random",
]
# 曲のidは小さい整数のため、SQLiteで扱えない大きさの値は入力エラーにする
SongId = Annotated[int, Field(ge=1, le=2147483647, description="曲のid")]


def _text(description):
    return Annotated[str | None, Field(description=description)]


def _flag(description):
    return Annotated[bool | None, Field(description=description)]


def _integer(description):
    return Annotated[int | None, Field(ge=1, description=description)]


def dump(data):
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def summarize_song(song, include_lyrics=False):
    summary = {key: song.get(key) for key in SONG_KEYS}
    summary["flags"] = [flag for flag in SONG_FLAGS if song.get(flag)]
    # 最も模倣された曲は1400件を超えるため、idの一覧ではなく数だけ返す
    summary["imitated_count"] = len(song.get("imitateds") or [])
    if include_lyrics:
        summary["lyrics"] = song.get("lyrics")
    return summary


def _shorten(cell):
    if isinstance(cell, str) and len(cell) > MAX_CHANGE_CELL:
        return f"{cell[:MAX_CHANGE_CELL]}…（省略。全{len(cell)}文字）"
    return cell


def summarize_history(history):
    changes = history.get("changes")
    if isinstance(changes, list) and all(isinstance(row, list) for row in changes):
        return {**history, "changes": [[_shorten(cell) for cell in row] for row in changes]}
    return history


async def fetch(client, path, params=None, not_found=None):
    try:
        return await client.get(path, params)
    except ApiError as e:
        if e.status == 404 and not_found:
            raise ToolError(not_found) from e
        raise ToolError(str(e)) from e


def create_server(client):
    server = MCPServer("subekashi", title="全て歌詞の所為です。", instructions=INSTRUCTIONS, version=__version__)
    # 結果は1つのJSONの文字列で返すため、構造化出力にすると同じ内容が二重に送られる
    tool = partial(server.tool, annotations=READ_ONLY, structured_output=False)

    @tool()
    async def search_songs(
        title: _text("タイトルの一部（部分一致）") = None,
        author: _text("作者名の一部（部分一致）。作者の別名義・略称も含めて探す") = None,
        lyrics: _text("歌詞の一部（部分一致）") = None,
        url: _text("動画などのURLの一部（部分一致）。https:// や www. の有無は問わない") = None,
        keyword: _text("タイトル・作者名（別名義を含む）・歌詞・URLのいずれかに含まれる語") = None,
        guesser: _text("タイトル・作者名（別名義を含む）・URLのいずれかに含まれる語。模倣元を探すときに使う") = None,
        title_exact: _text("タイトル（完全一致）") = None,
        author_exact: _text("作者名（完全一致）。作者の別名義・略称も含めて探す") = None,
        prush: _text("プレミアラッシュ（プレラ）の名前（完全一致）") = None,
        imitate: _integer("曲のidを渡すと、その曲を模倣している曲（模倣曲）を探す") = None,
        imitated: _integer("曲のidを渡すと、その曲が模倣している曲（模倣元）を探す") = None,
        categorys: _text(
            "カテゴリをカンマ区切りで指定する。先頭に ~ を付けたカテゴリは除く。"
            "song（曲）arrange（アレンジ）otomad（音MAD）medley（メドレー）omnibus（総集編）notice（予告）offv（オフボ）cover（カバー）meme（ネタ動画）。"
            "例: arrange,cover はアレンジかカバー、~meme はネタ動画以外"
        ) = None,
        mediatypes: _text(
            "動画などの置き場所をカンマ区切りで指定する。"
            "youtube x nicovideo soundcloud vimesis scratch bandcamp drive bilibili imicom linkcore bandlab newgrounds note TikTok vidlii bluesky bowlroll misskey booth piapro rechord dropbox、"
            "URLが未登録の曲は other"
        ) = None,
        is_subeana: _flag("すべあな界隈曲か。falseですべあな界隈曲以外") = None,
        is_original: _flag("オリジナル模倣曲か") = None,
        is_joke: _flag("ネタ曲か。falseでネタ曲を除く") = None,
        is_inst: _flag("インスト曲か") = None,
        is_draft: _flag("下書きか") = None,
        is_deleted: _flag("動画が非公開・削除済みか。falseで公開されている曲だけ") = None,
        is_limited: _flag("限定公開か") = None,
        is_questionable: _flag("界隈曲かどうか議論の余地があり、人によって認識が異なる曲か") = None,
        is_special: _flag("スペシャルデザインか") = None,
        is_lack: _flag("情報が不足している曲か（URL・模倣元・歌詞のいずれかが未登録）") = None,
        is_collab: _flag("作者が2人以上の合作か") = None,
        view_gte: _integer("YouTubeの再生回数がこれ以上。指定するとYouTubeの動画がある曲だけになる") = None,
        view_lte: _integer("YouTubeの再生回数がこれ以下。指定するとYouTubeの動画がある曲だけになる") = None,
        like_gte: _integer("YouTubeの高評価数がこれ以上。指定するとYouTubeの動画がある曲だけになる") = None,
        like_lte: _integer("YouTubeの高評価数がこれ以下。指定するとYouTubeの動画がある曲だけになる") = None,
        upload_time_gte: _text("YouTubeの投稿日時がこれ以降（例: 2024-01-01 や 2024-01-01T00:00:00）。指定するとYouTubeの動画がある曲だけになる") = None,
        upload_time_lte: _text("YouTubeの投稿日時がこれ以前（例: 2024-01-01 や 2024-01-01T00:00:00）。指定するとYouTubeの動画がある曲だけになる") = None,
        sort: Annotated[SongSort, Field(description="並び替え。先頭に - を付けると降順。post_timeは更新日、upload_timeはYouTubeの投稿日。randomはランダム。ページをまたいで順に取得するときは固定の順序にする")] = "id",
        page: Annotated[int, Field(ge=1, description="何ページ目か（1から）")] = 1,
        size: Annotated[int, Field(ge=1, le=100, description="1ページの件数")] = 20,
        include_lyrics: Annotated[bool, Field(description="歌詞も返すか。歌詞は長いので、必要なときだけtrueにする。1曲の歌詞はget_songでも取得できる")] = False,
    ) -> str:
        """曲を検索する。指定した条件をすべて満たす曲を、件数（count）と合わせて返す。

        結果の各曲は id・title・authors（作者のidと名前）・url（動画などのURL）・category・flags（当てはまる真偽値の名前）・
        prush・post_time（サイトでの更新日時）・upload_time・view・like（YouTubeの投稿日時・再生回数・高評価数）・
        imitates（模倣元の曲のid）・imitated_count（模倣曲の数）を持つ。歌詞は include_lyrics=true のときだけ付く。
        結果が多いときは page を増やして続きを取得する（max_page が最後のページ）。
        """
        # 引数の名前はそのままAPIのクエリの名前。localsにはクロージャで参照するclientも入るため除く
        params = {name: value for name, value in locals().items() if name not in ("client", "include_lyrics")}
        data = await fetch(client, "/api/song/", params)
        return dump({**data, "result": [summarize_song(song, include_lyrics) for song in data["result"]]})

    @tool()
    async def get_song(song_id: SongId) -> str:
        """曲1件の詳細を、歌詞の全文も含めて取得する。

        search_songs の結果と同じ項目に lyrics が加わる。この曲を模倣している曲の一覧は、
        search_songs の imitate にこの曲のidを渡して取得する。
        """
        song = await fetch(client, f"/api/song/{song_id}/", not_found=f"曲 {song_id} は見つかりません。削除された曲かもしれません。")
        return dump(summarize_song(song, include_lyrics=True))

    @tool()
    async def get_author(author_id: Annotated[int, Field(ge=1, le=2147483647, description="作者のid")]) -> str:
        """作者1人の詳細（名前・別名・リンク）を取得する。

        別名の種類（alias_type）は id（ID）abbr（略称）common（通称）past（以前の名称）sns（SNSでの名称）spell（表記揺れ）another（別名義）group（グループ）。
        作者のidは、曲の authors から得る。作者名から曲を探すには search_songs の author_exact を使う。
        """
        author = await fetch(client, f"/api/author/{author_id}/", not_found=f"作者 {author_id} は見つかりません。")
        return dump(author)

    @tool()
    async def get_song_history(
        song_id: SongId,
        page: Annotated[int, Field(ge=1, description="何ページ目か（1から）")] = 1,
        size: Annotated[int, Field(ge=1, le=50, description="1ページの件数")] = 10,
    ) -> str:
        """曲の編集履歴を、新しい順に取得する。

        各履歴は id・history_type（new 新規作成 / edit 編集 / delete 削除 / restore 削除の取り消し）・title（見出し）・
        create_time（編集日時）・changes（編集内容の表。先頭の行が見出しで、以降が変更点）・
        editor（編集者のid。編集履歴を非公開にしている編集者は null）を持つ。
        changes の1つの欄が1000文字を超えるときは、切り詰めて全体の文字数を付ける。
        """
        data = await fetch(client, "/api/history/", {"song": song_id, "page": page, "size": size})
        return dump({**data, "result": [summarize_history(history) for history in data["result"]]})

    return server


def main():
    create_server(Client()).run()
