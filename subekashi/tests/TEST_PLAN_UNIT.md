# テスト計画書

作成日: 2026-04-07

## 概要

このドキュメントは `subekashi` プロジェクト全体のテスト計画をまとめたものです。
現状、`test_author_migration.py` にAuthor関連の基本テストが存在しますが、全体的なカバレッジは低い状態です。

---

## 既存テスト

| ファイル | テストクラス | 状態 |
| --- | --- | --- |
| `tests/test_author_migration.py` | AuthorModelTest, SongAuthorRelationshipTest, AuthorHelpersTest, AuthorViewTest, ChannelRedirectTest, SongDisplayTest | 作成済み |
| `tests/song.py` | SongPageTest | 外部API依存（結合テスト）|

---

## テスト計画一覧

---

### 1. `lib/url.py` — URL処理ユーティリティ

**テストファイル案**: `tests/test_lib_url.py`

#### 1-1. `is_youtube_url(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常のYouTube URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `True` |
| YouTubeショートURL | `https://youtube.com/shorts/abcdefghijk` | `True` |
| 短縮YouTube URL (youtu.be) | `https://youtu.be/dQw4w9WgXcQ` | `True` |
| モバイル版YouTube URL | `https://m.youtube.com/watch?v=dQw4w9WgXcQ` | `True` |
| 非YouTube URL | `https://nicovideo.jp/watch/sm12345` | `False` |
| 空文字列 | `""` | `False` |

#### 1-2. `get_youtube_id(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| youtu.be URL | `https://youtu.be/dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| ショートURL | `https://youtube.com/shorts/abcdefghijk` | `"abcdefghijk"` |
| 非YouTube URL | `https://example.com` | `"https://example.com"` (そのまま返す) |

#### 1-3. `format_youtube_url(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常YouTube URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"https://youtu.be/dQw4w9WgXcQ"` |
| 既に短縮済み | `https://youtu.be/dQw4w9WgXcQ` | `"https://youtu.be/dQw4w9WgXcQ"` |
| 非YouTube URL | `https://nicovideo.jp/watch/sm12345` | `"https://nicovideo.jp/watch/sm12345"` (変化なし) |

#### 1-4. `format_x_url(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| Twitter URL (クエリあり) | `https://twitter.com/user/status/123?s=20` | `"https://x.com/user/status/123"` |
| x.com URL | `https://x.com/user/status/123` | `"https://x.com/user/status/123"` |
| 非X URL | `https://example.com/path?q=1` | そのまま返す |

#### 1-5. `clean_url(urls)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| スペース付きカンマ区切り | `"url1, url2"` | `"url1,url2"` |
| www付きURL | `"https://www.youtube.com/watch?v=abc1234abcd"` | `"https://youtu.be/abc1234abcd"` |
| Googleリダイレクトリンク | `"https://www.google.com/url?q=https://youtu.be/abc1234abcd"` | `"https://youtu.be/abc1234abcd"` |
| 複数URL | `"https://youtu.be/abc1234abcd,https://x.com/u/1"` | 各URLが正規化されたカンマ区切り |

#### 1-6. `get_allow_media(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| Bluesky URL | `https://bsky.app/profile/example.bsky.social` | `result["id"] == "bluesky"` |
| Vimesis URL | `https://main.vimesis.com/channel/@subekashi` | `result["id"] == "vimesis"` |
| note URL | `https://note.com/articles/abc123` | `result["id"] == "note"` |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（Vimesis） | `https://vimesisXcom.example.net/` | `False`（Issue #1056） |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（YouTube） | `https://youtuXbe.example.net/` | `False`（Issue #1056） |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（X） | `https://xXcom.example.net/` | `False`（Issue #1056） |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（ニコニコ動画） | `https://nicovideoXjp.example.net/` | `False`（Issue #1056） |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（SoundCloud） | `https://soundcloudXcom.example.net/` | `False`（Issue #1056） |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（Bandcamp） | `https://bandcampXcom.example.net/` | `False`（Issue #1056） |
| ドメイン内の`.`が未エスケープだと誤マッチする文字列（ビリビリ動画） | `https://bilibiliXcom.example.net/` | `False`（Issue #1056） |
| 末尾側の境界チェックがないとなりすませるドメイン（Vimesis） | `https://vimesis.com.attacker.example/` | `False`（Issue #1056 レビュー指摘） |
| 先頭側の境界チェックがないとなりすませるドメイン（note） | `https://xnote.comevil.net/` | `False`（Issue #1056 レビュー指摘） |

---

### 2. `lib/song_service.py` — 曲サービス

**テストファイル案**: `tests/test_lib_song_service.py`

#### 2-1. `check_reject_list(authors)`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| NGリストに含まれる作者 | `REJECT_LIST = ["NGアーティスト"]`、該当Authorオブジェクト | エラーメッセージ文字列を返す |
| NGリストに含まれない作者 | 通常のAuthorオブジェクト | `None` を返す |
| REJECT_LISTがインポートできない場合 | ImportError発生 | `None` を返す (空リスト扱い) |
| 空のauthorsリスト | `[]` | `None` を返す |

#### 2-2. `validate_song_url(cleaned_url, exclude_song_id=None)`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 既存URLと重複する | SongLinkが既に存在し曲に紐付いている | エラーメッセージ文字列を返す |
| 重複しないURL | 新しいURL | `None` を返す |
| 自分自身を除外した場合 | `exclude_song_id` を指定し、同じ曲のURL | `None` を返す |
| `allow_dup=True` のSongLink | 重複URLだが `allow_dup=True` | `None` を返す |
| 曲に紐付いていないSongLink | リンクは存在するが曲なし | `None` を返す |
| URLが`SongLink.url`のmax_length丁度 (#1085) | `len(url) == max_length` | `None` を返す |
| URLが`SongLink.url`のmax_length超過 (#1085) | `len(url) == max_length + 1` | エラーメッセージ文字列を返す（MySQL移行時のData too long for column対策） |

#### 2-3. `create_song(fields)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な曲作成 | 有効な `SongFields` | Songオブジェクトが保存される |
| `post_time` が自動設定される | fields に `post_time` なし | `timezone.now()` に近い時刻が設定される |
| 各フラグが正しく設定される | `is_original=True`, `is_joke=False` など | Song属性がfieldsと一致する |
| `is_questionable` が正しく設定される | `is_questionable=True` | `song.is_questionable` が `True` |

#### 2-4. `get_imitate_songs(imitates_str, self_id)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| カンマ区切りのID | `"1,2,3"`, `self_id=0` | 存在するSongのリスト |
| 自分自身のIDを含む | `"1,2"`, `self_id=1` | IDが1の曲は除外される |
| 数値以外の文字列を含む | `"1,abc,2"` | 数値のみ処理、例外なし |
| 空文字列 | `""` | 空のリスト |
| スペースを含む | `" 1 , 2 "` | 正常に処理される |

#### 2-5. `update_song(song, fields, author_objects, imitate_songs, cleaned_url_list)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 既存URLの削除 | 新しいURLリストに含まれないURL | `SongLink.songs` から削除される |
| 他の曲に紐付かないURLは完全削除 | URLが他の曲にない | SongLinkレコードごと削除される |
| 新しいURLの追加 | 新しいURL | SongLinkが作成・紐付けられる |
| 作者の更新 | 新しい author_objects | Song.authors が更新される |
| `is_questionable` の更新 | `is_questionable=True` | `song.is_questionable` が `True` に更新される |
| トランザクション失敗時のロールバック | DB エラーを模擬 | 変更が元に戻る |

#### 2-6. `build_delete_discord_text(song, reason, editor)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常なテキスト生成 | 曲オブジェクト、理由、編集者 | 曲ID・タイトル・作者・理由を含む文字列 |

#### 2-7. `build_edit_song_discord_text(song_id, song, fields, author_objects, cleaned_url, imitate_songs)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| タイトル変更 | before と after が異なるタイトル | 変更差分が `changes` リストに含まれる |
| 変更なし | before と after が同じ | `changed_labels` が空リスト |
| 複数フィールドの変更 | 複数の差分 | 全変更が `changes` に含まれ、`edit_title` に反映 |
| `is_questionable` の変更 | before/after で `is_questionable` が異なる | `changed_labels` に「界隈曲?」が含まれる |

---

### 3. `lib/query_filters.py` — クエリフィルター

**テストファイル案**: `tests/test_lib_query_filters.py`

#### 3-1. `filter_by_keyword(keyword)`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| タイトル部分一致 | キーワードがタイトルに含まれる曲 | その曲が結果に含まれる |
| 作者名部分一致 | キーワードが作者名に含まれる | その曲が結果に含まれる |
| 歌詞部分一致 | キーワードが歌詞に含まれる | その曲が結果に含まれる |
| URL部分一致 | キーワードがURLに含まれる | その曲が結果に含まれる |
| 一致なし | 存在しないキーワード | 空のクエリセット |
| 別名（正方向）一致 | `author(yamada)` の別名が `sasaki`、`Author(sasaki)` が別途存在。keyword=`sasaki` | `yamada` の曲・`sasaki` の曲の両方が結果に含まれる |
| 別名（逆方向）一致 | 上記と同じ前提。keyword=`yamada` | 双方向解決により `yamada` の曲・`sasaki` の曲の両方が結果に含まれる |
| 対象authorが存在しない別名 | `author` の別名が `single_alias`（`Author(single_alias)` は未登録） | keyword=`single_alias` で正方向のみヒットする |

`yamada`/`sasaki`のように、owner名とtarget名が互いの部分文字列にならない組み合わせを使う。
`foo`/`foo_sub`のような包含関係だと、素の作者名一致（`icontains`/`contains`）だけで
逆方向テストが偶然パスしてしまい、別名解決コードを経由したかどうかを検証できないため。

#### 3-1-1. `filter_by_author(value)` / `filter_by_author_exact(value)`（`filter_by_author_alias`経由の別名・双方向対応）

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 作者名の部分一致 | `authors__name`に一致 | 結果に含まれる |
| 別名（正方向）の部分一致 | `filter_by_keyword`と同様の`yamada`/`sasaki`構成、keyword=`sasaki` | `yamada`・`sasaki`双方の曲が結果に含まれる |
| 別名（逆方向）の部分一致 | 上記と同じ前提、keyword=`yamada` | `yamada`・`sasaki`双方の曲が結果に含まれる |
| 完全一致（`_exact`） | 部分文字列のみ指定 | 一致せず結果に含まれない |
| 完全一致（`_exact`、別名逆方向） | `author.name`に完全一致する値を指定 | 双方向解決により別名先の曲も結果に含まれる |

#### 3-1-2. `filter_by_guesser(guesser)`（別名・双方向対応、URL検索対応 #1117）

URLでの検索は`clean_url`で正規化した値に対する`links__url__icontains`で行う。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| タイトル一致 | タイトルに検索語を含む曲 | 結果に含まれる |
| 作者名一致 | 作者名に検索語を含む曲 | 結果に含まれる |
| 別名（正方向・逆方向）一致 | `filter_by_keyword`と同様の`yamada`/`sasaki`構成 | 正方向・逆方向いずれの検索語でも双方の曲が結果に含まれる |
| URL完全一致（#1117） | `https://youtu.be/guessUrl001`のSongLinkが紐付いた曲 | 同URLで検索すると結果に含まれ、無関係な曲は含まれない |
| URL部分一致（#1117） | 同上 | 動画ID`guessUrl001`のみで検索しても結果に含まれる |
| 正規化前のYouTube URL（#1117） | 同上 | `https://www.youtube.com/watch?v=guessUrl001`で検索しても`clean_url`による正規化で結果に含まれる |
| URLの大文字小文字を区別しない（#1117） | 同上 | `GUESSURL001`で検索しても結果に含まれる |
| 別のURL（#1117） | 同上 | `https://youtu.be/otherUrl999`で検索すると結果に含まれない |

#### 3-1-3. `alias_type="another"`（別名義）の除外（#996）

`another`は同一人物が運用していても意図的に区別して扱うべきものであり、双方向解決（検索）の対象外とする。
`filter_by_author` / `filter_by_author_exact` / `filter_by_keyword` / `filter_by_guesser` すべてに共通の挙動。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 正方向・`alias_type=another` | ownerの別名(`alias_type="another"`)のnameで検索 | ownerの曲は結果に含まれない（target自身の曲のみヒット） |
| 逆方向・`alias_type=another` | owner自身のnameで検索 | target側の曲は結果に含まれない |
| 同一ownerに`another`以外の別名も存在 | `another`の別名と`past`の別名を両方持つowner | `past`側の別名名での検索は通常通りヒットする（`another`の存在に影響されない） |

#### 3-1-4. `alias_type="group"`（グループ）の除外（仕様変更、#1006）

`group`は`another`と同様に、検索では正方向・逆方向とも一切考慮しない。メンバー名義で
検索してもグループ自身の曲はヒットせず、グループ名義で検索してもメンバー個々の曲は
ヒットしない。#1006では当初メンバー→グループの片方向のみ考慮する非対称ルールを実装
したが、フィードバック元への再確認により、検索では完全除外する方針に変更した
（一覧画面での「直接の関係は常に表示する」ルールには影響しない。詳細は#1003参照）。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 正方向・`alias_type=group` | memberの別名(`alias_type="group"`)にgroupのnameを登録 | group自身の曲は結果に含まれない（member自身の曲のみヒット） |
| 逆方向・`alias_type=group` | 同上 | member自身の曲は結果に含まれない |
| 完全一致（`_exact`）・`alias_type=group` | 同上 | group自身の曲は結果に含まれない |
| `filter_by_keyword`・`alias_type=group` | 同上 | group自身の曲は結果に含まれない |
| `filter_by_guesser`・`alias_type=group` | 同上 | group自身の曲は結果に含まれない |
| 同一memberに`group`以外の別名も存在 | `group`の別名と`past`の別名を両方持つmember | `past`側の別名名での検索は通常通りヒットする（`group`の存在に影響されない） |

#### 3-1-5. 推移的関係解決の検索への適用（仕様変更、#1006）

#1003で確認された具体例（名義Aに別名義B・以前の名称C・以前の名称D・グループEを登録）が、
`filter_by_author_exact`で以下の検索結果になることを確認する結合テスト。

| テストケース | 検索語 | 期待結果 |
| --- | --- | --- |
| Aで検索 | `tamura`(A) | A, C, D の曲がヒットする（B・Eは含まれない） |
| Bで検索 | `inoue`(B) | Bの曲のみヒットする（`another`は中継点にならない） |
| Cで検索 | `kobayashi`(C) | A, C, D の曲がヒットする（`past`経由でAを介してDに到達。Eは含まれない） |
| Dで検索 | `yoshida`(D) | A, C, D の曲がヒットする（Cと対称） |
| Eで検索 | `watanabe`(E) | Eの曲のみヒットする（`group`は中継点にならず、検索では完全除外される） |

#### 3-1-6. 別名を辿る処理の一括読み込み（#1162）

`_bridging_cluster`は中継点になる別名（`another`・`group`以外）を1クエリでまとめて読み込み、Python側で辿る。
A -`past`-> B -`spell`-> C -`abbr`-> D とつながり、DとEは`another`でのみつながる構成で、`filter_by_author_exact`の結果を確認する。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 正方向に複数ホップ | `hop_a`(A)で検索 | A, B, C, D の曲がヒットする（Eは含まれない） |
| 逆方向に複数ホップ | `hop_d`(D)で検索 | A, B, C, D の曲がヒットする（Eは含まれない） |
| `another`は中継しない | `hop_e`(E)で検索 | Eの曲のみヒットする |
| クエリ数（起点1件） | `past`の別名を持つ作者1人が検索語にマッチ | `filter_by_author`のクエリ数が3（作者名・別名の取得2＋別名の一括取得1） |
| クエリ数（起点30件） | `past`の別名を持つ作者30人が検索語にマッチ | クエリ数が起点1件の場合と同じ3のまま |

#### 3-2. `filter_by_lack()`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| URLなし・削除されていない曲 | `is_deleted=False`, SongLink なし | 結果に含まれる |
| 歌詞なし・インストではない曲 | `is_inst=False`, `lyrics=""` | 結果に含まれる |
| すべて完備している曲 | URL・歌詞・作者あり | 結果に含まれない |
| `is_subeana=True` かつ特殊作者(id=1)なしの曲 | `is_original=False`, `is_subeana=True`, `imitates`なし, 特殊作者(id=1)の紐付けなし | 結果に含まれる |
| 特殊作者(id=1)が紐づいている曲 | 上記に加え特殊作者(id=1)を紐付け | 結果に含まれない |
| `is_subeana=False` の曲 | `is_original=False`, `is_subeana=False` | 結果に含まれない |
| `is_questionable=True` かつURLなし・削除されていない曲 | `is_questionable=True`, `is_deleted=False`, SongLink なし | 結果に含まれる（URLなし条件は `is_questionable` を問わない） |
| `is_questionable=True` かつ歌詞なし/模倣なし等の曲 | `is_questionable=True`, URLあり、歌詞なし等 | 結果に含まれない（歌詞なし・模倣なし条件は `is_questionable=False` が必須） |

#### 3-3. `filter_by_mediatypes(mediatypes)`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| `other`（URL未登録） | SongLink が1件も紐付いていない曲 | 結果に含まれる |
| `other`（URL未登録） | SongLink が紐付いている曲 | 結果に含まれない |
| `other`（URL未登録） | SongLink なし かつ `is_deleted=True`（非公開/削除済み） | 結果に含まれない |
| 個別メディアタイプ（例: `youtube`） | 該当URLのSongLinkが紐付いている曲 | 結果に含まれる。URLなしの曲は含まれない |
| 複数指定（例: `youtube,other`） | URLありの曲・URLなしの曲がそれぞれ存在 | 両方とも結果に含まれる |
| `vimesis`（DB REGEXP経由の境界チェック確認） | `https://main.vimesis.com/channel/@subekashi` のSongLinkが紐付いている曲 | 結果に含まれる。YouTube曲は含まれない（Issue #1056） |
| `vimesis`（なりすましドメインの除外確認） | `https://vimesis.com.attacker.example/` のSongLinkが紐付いている曲 | 結果に含まれない（Issue #1056 レビュー指摘） |

#### 3-4. `make_is_lack_annotation()`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 未完成の曲に annotate | 上記の `filter_by_lack` と同じ条件 | `is_lack=True` がアノテートされる |
| 完成した曲に annotate | URLと歌詞が揃っている曲 | `is_lack=False` がアノテートされる |
| `is_subeana=True` かつ特殊作者(id=1)なしの曲に annotate | `is_original=False`, `is_subeana=True`, `imitates`なし, 特殊作者(id=1)の紐付けなし | `is_lack=True` がアノテートされる |
| 特殊作者(id=1)が紐づいている曲に annotate | 上記に加え特殊作者(id=1)を紐付け | `is_lack=False` がアノテートされる |
| `is_questionable=True` かつURLなし・削除されていない曲に annotate | `is_questionable=True`, SongLink なし | `is_lack=True` がアノテートされる（URLなし条件は `is_questionable` を問わない） |
| `is_questionable=True` かつ歌詞なし等の曲に annotate | `is_questionable=True`, URLあり、歌詞なし等 | `is_lack=False` がアノテートされる（歌詞なし条件は `is_questionable=False` が必須） |

#### 3-5. `filter_by_collab()`（#943）

作者が2人以上の曲を合作とする（曲カードの「合作」の表示と同じ条件）。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| filterで合作の曲のみ | 作者なし・作者1人・作者2人・作者3人の曲が存在 | 作者2人・3人の曲のみ含まれ、重複しない |
| excludeで合作以外の曲 | 同上 | 作者なし・作者1人の曲のみ含まれる |

---

### 4. `lib/query_utils.py` — クエリユーティリティ

**テストファイル案**: `tests/test_lib_query_utils.py`

#### 4-1. `clean_query_params(query_params)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常の辞書 | `{"key": "value"}` | `{"key": "value"}` |
| リスト形式の値 | `{"key": ["first", "second"]}` | `{"key": "first"}` |
| 空のリスト | `{"key": []}` | `{"key": []}` (変化なし) |
| 混合 | `{"a": "val", "b": ["x", "y"]}` | `{"a": "val", "b": "x"}` |

#### 4-2. `has_view_filter_or_sort(query_data)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| `view_lte` が存在する | `{"view_lte": "100"}` | `True` |
| `sort=view` | `{"sort": "view"}` | `True` |
| `sort=-view` | `{"sort": "-view"}` | `True` |
| 関係ないキー | `{"sort": "title"}` | `False` |
| 空辞書 | `{}` | `False` |

#### 4-3. `has_like_filter_or_sort(query_data)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| `like_lte` が存在する | `{"like_lte": "50"}` | `True` |
| `sort=like` | `{"sort": "like"}` | `True` |
| `sort=-like` | `{"sort": "-like"}` | `True` |
| 空辞書 | `{}` | `False` |

#### 4-4. `has_upload_time_sort(query_data)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| `sort=upload_time` | `{"sort": "upload_time"}` | `True` |
| `sort=-upload_time` | `{"sort": "-upload_time"}` | `True` |
| 別のソート | `{"sort": "title"}` | `False` |
| 空辞書 | `{}` | `False` |
| view系ソート | `{"sort": "view"}` | `False` |
| like系ソート | `{"sort": "like"}` | `False` |

#### 4-5. `has_youtube_filter_or_sort(query_data)`（#970）

`YOUTUBE_FILTERS`・`YOUTUBE_SORTS` は `SongFilter.qs()` と曲の検索画面（songs.js）の案内表示で共通して使用する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| YouTube関連のフィルタ | `YOUTUBE_FILTERS` の各キー | `True` |
| YouTube関連のソート | `YOUTUBE_SORTS` の各ソート（upload_timeを含む） | `True` |
| 別のソート | `{"sort": "-post_time"}` | `False` |
| 別のフィルタ | `{"title": "テスト", "mediatypes": "youtube"}` | `False` |
| 空辞書 | `{}` | `False` |

---

### 5. `lib/author_helpers.py` — 作者ヘルパー

**テストファイル案**: `tests/test_lib_author_helpers.py` （既存の `test_author_migration.py` に追加可能）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 新規作者の一括作成 | `["新作者A", "新作者B"]` | 2つのAuthorが作成されDBに保存 |
| 既存作者は新規作成しない | DBに存在する作者名 | 同じAuthorオブジェクトが返される（重複なし）|
| 空文字列をスキップ | `["作者A", "", "作者B"]` | 空文字列を除いた2件のAuthor |
| 全て空文字列 | `["", ""]` | 空のリスト |
| `alias_type="past"`の別名は現在の名義に正規化される (#1008) | 入力が`past`別名の`name`と完全一致 | 新規Authorを作らず、その別名の`author`（＝統一した名義）を返す |
| `alias_type="past"`以外は正規化されない (#1008) | 入力が`another`別名の`name`と完全一致 | 入力文字列のまま新規Authorとして作成される（意図的に区別すべき別人格を巻き込まないため） |
| past正規化とREJECT_LISTすり抜け防止 (#1008) | REJECT_LIST登録済みauthorのpast別名で入力 | `get_or_create_authors()`が現在の名義に正規化するため、`check_reject_list()`が正しく検知できる |
| past別名の一括取得 (#1008) | past別名5件を含む入力 | past別名の存在チェックが名前ごとに都度クエリを発行せず、1クエリで一括取得される（N+1にならない） |

#### 5-1. `validate_author_name_lengths(author_names)`（#1085）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 上限内の名前のみ | `["作者A", "作者B"]` | `None` を返す |
| `Author.name`のmax_length丁度 | `len(name) == max_length` | `None` を返す |
| `Author.name`のmax_length超過 | `len(name) == max_length + 1` | エラーメッセージ文字列を返す（MySQL移行時のData too long for column対策） |
| 空文字列はスキップ | `["", "作者A", ""]` | `None` を返す |

---

### 6. `forms.py` — フォームバリデーション

**テストファイル案**: `tests/test_forms.py`

#### 6-1. `ContactForm`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な入力 | `category="不具合の報告"`, `detail="詳細内容"` | `is_valid() == True` |
| categoryが空 | `category=""`, `detail="内容"` | `is_valid() == False`、エラーメッセージあり |
| detailが空 | `category="質問"`, `detail=""` | `is_valid() == False`、エラーメッセージあり |
| 不正なcategory値 | `category="不正な選択肢"` | `is_valid() == False` |
| detailが10000文字丁度 (#1085) | `detail="あ" * 10000` | `is_valid() == True` |
| detailが10000文字超 (#1085) | `detail="あ" * 10001` | `is_valid() == False` |

#### 6-2. `SongDeleteForm`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な入力 | `reason="削除理由の詳細"` | `is_valid() == True` |
| reasonが空 | `reason=""` | `is_valid() == False`、`"削除理由を入力してください。"` |

#### 6-3. `SongEditForm`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 最低限の必須フィールドのみ | `title="タイトル"`, `authors="作者名"` | `is_valid() == True` |
| titleが空 | `title=""`, `authors="作者名"` | `is_valid() == False`、`"タイトルが未入力です。"` |
| authorsが空 | `title="タイトル"`, `authors=""` | `is_valid() == False`、`"作者は空白にできません。"` |
| urlは任意 | `url=""` (省略) | `is_valid() == True` |
| is_original など boolean フラグ | `is_original=True` | `cleaned_data["is_original"] == True` |
| is_questionable boolean フラグ | `is_questionable=True` | `cleaned_data["is_questionable"] == True` |
| titleが500文字超 | `title="あ" * 501` | `is_valid() == False` |
| lyricsが10000文字丁度 (#1085) | `lyrics="あ" * 10000` | `is_valid() == True` |
| lyricsが10000文字超 (#1085) | `lyrics="あ" * 10001` | `is_valid() == False` |

#### 6-4. `AuthorAliasForm`（#992）

DBアクセス（重複チェック）を伴うため `TestCase` を使用する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な入力 | `name="別名A"`, `alias_type="past"` | `is_valid() == True` |
| nameが空 | `name=""` | `is_valid() == False` |
| 不正なalias_type | `alias_type="不正な種別"` | `is_valid() == False` |
| CHOICES全ての値 | `alias_type`にCHOICESの各キー | いずれも `is_valid() == True` |
| nameがauthor自身のnameと同じ | `name=author.name` | `is_valid() == False`、`"作者自身の名前は別名として登録できません。"` |
| nameが既存のAuthorAlias.nameと重複 | 既存のname | `is_valid() == False`、`"その別名は既に登録されています。"` |
| 編集時に自分自身のnameのまま | `editing_alias=alias`, `name=alias.name` | `is_valid() == True`（自分自身は重複チェックから除外） |
| 編集時に他のaliasのnameと重複 | `editing_alias=alias`, `name=`他のalias.name | `is_valid() == False` |
| `group`名を別のauthorが登録 (#1044) | 既に別authorが`alias_type="group"`で登録済みの名前を、`alias_type="group"`で別authorが登録 | `is_valid() == True`（groupは複数authorでの共有を許可する） |
| 同一authorによる`group`名の重複 (#1044) | 自分自身が既に`alias_type="group"`で登録済みの名前を、再度`alias_type="group"`で登録 | `is_valid() == False`、`"その別名は既に登録されています。"` |
| `group`名がgroup以外の別名と衝突 (#1044) | `alias_type`がgroup以外の既存別名と同じ名前を`alias_type="group"`で登録 | `is_valid() == False`（groupの緩和はgroup同士に限定） |
| group以外の種別が既存の`group`名と衝突 (#1044) | 既存の`alias_type="group"`の別名と同じ名前を、group以外の種別で登録 | `is_valid() == False`（groupの緩和はgroup同士に限定） |

#### 6-5. `AuthorUnifyNameForm`（#1008、#1137）

DBアクセス（候補・衝突チェック）を伴うため `TestCase` を使用する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 現在のAuthor.nameを選択 | `name=author.name` | `is_valid() == True` |
| `alias_type="past"`の別名を選択 | `name=`past別名のname | `is_valid() == True` |
| `alias_type="past"`以外（例: another）は候補外 | `name=`another別名のname | `is_valid() == False`、`"選択できない名義です。"` |
| 全く関係ない名前 | `name="全く関係ない名前"` | `is_valid() == False`、`"選択できない名義です。"` |
| past別名の名前が別のAuthorと衝突 | 別Authorが同名で実在する状態で`name=`該当past別名のname | `is_valid() == True`（そのAuthorを統一先とする処理はAuthorUnifyNameSetView側で行う、#1029、#1137） |

---

### 7. ビュー — ページアクセスと HTTP レスポンス

**テストファイル案**: `tests/test_views.py`

#### 7-1. `TopView` (`/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| テンプレートが使用される | GETリクエスト | `subekashi/top.html` がレンダリングされる |
| ニュース欄のリンク付与（#961） | `tag="news"`, `handle_as_news=False`の記事 | タイトルのみ表示され`<a>`タグは付与されない |
| ニュース欄のリンク付与（#961） | `tag="release"`の記事 | `DefaultArticleView`へのURLでタイトル全体が`<a>`タグにくくられる |
| ニュース欄のリンク付与（#961） | `handle_as_news=True`の記事（`tag`は`news`以外） | `DefaultArticleView`へのURLでタイトル全体が`<a>`タグにくくられる |
| ニュース欄のリンク付与（#961） | `tag="news"`かつ`handle_as_news=True`の記事 | `handle_as_news`が優先され、リンクが付与される |
| タイトル中のリンクの除去（#483） | `tag="release"`でタイトルが`[リンク](https://example.com)と**太字**` | `<a>`が入れ子にならないよう、タイトル中のリンクだけ外して`<a href='（記事のURL）'>リンクと<strong>太字</strong></a>`になる |
| タイトル中のリンクの保持（#483） | `tag="news"`, `handle_as_news=False`でタイトルにリンクを含む | リンクでくくらないため、タイトル中のリンクはそのまま表示される |
| 作成された歌詞の表示 | `genetype="janome", score=5`のAiレコードが存在 | 「作成された歌詞」欄に表示される |
| レガシーgenetype="model"は対象外（GPTインポート廃止） | `genetype="model", score=5`のレコードが存在 | 「作成された歌詞」欄に表示されない（`get_top_scored()`も`genetype="janome"`のみ対象） |
| PC向けグローバルヘッダーの配置（#1123） | `pc_menu_position`クッキーなし（トップ） | `#pc-global-header`が`#pc-header-menu`の中に1つだけ置かれる |
| PC向けグローバルヘッダーの配置（#1123） | `pc_menu_position=aside`（サイド） | `#pc-header-menu`は無く、`#pc-global-header`が`#subekashi-header`より前に1つだけ置かれる |
| viewportのmetaタグ（#1058） | GETリクエスト | `<meta name="viewport" content="width=device-width,...">`が含まれ、余分な`meta=""`属性が無い |

#### 7-2. `SongsView` (`/songs/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| キーワード検索 | `?keyword=テスト` | HTTP 200、結果が絞られる |
| ページネーション | `?page=2&size=10` | HTTP 200 |
| 不正なページ番号 | `?page=abc` | HTTP 200 (デフォルト page=1 で処理) |
| 真偽値クエリ (大文字True) | `?is_draft=True` | context["is_draft"] = "True" (下書きのみ) |
| 真偽値クエリ (数値1) | `?is_draft=1` | context["is_draft"] = "True" |
| 真偽値クエリ (大文字False) | `?is_draft=False` | context["is_draft"] = "False" (下書き以外) |
| 真偽値クエリ (数値0) | `?is_draft=0` | context["is_draft"] = "False" |
| 真偽値クエリ (不正な値) | `?is_draft=abc` | context に is_draft が含まれない（フィルタなし） |
| 真偽値クエリ False の表示 | `?is_lack=False` | 「以外」のラジオボタンが選択された状態で表示される |
| 真偽値クエリ 未指定の表示 | URLクエリなし | 「指定なし」のラジオボタンが選択された状態で表示される |
| 真偽値フィルタは重複して表示しない | `?is_inst=True&is_original=False` | インスト曲・オリジナル模倣曲のラジオボタンはそれぞれ1つのフォームにのみ表示される |
| スペシャルデザインのフィルタ（#939） | `?is_special=True` | 「スペシャルデザイン」のラジオボタン（`fas fa-magic`）が表示され、`is_special-true`（のみ）のラジオボタンが1つだけ選択された状態で表示される |
| 合作のフィルタ（#943） | `?is_collab=True` | 「合作」のラジオボタン（`fas fa-user-friends`）が表示され、`is_collab-true`（のみ）のラジオボタンが1つだけ選択された状態で表示される |
| 界隈曲の種類・ネタ曲のラジオボタン | `?is_subeana=xx&is_joke=False` | 「以外」(`songrange-xx`・`jokerange-off`) のラジオボタンが選択された状態で表示される（選択肢は「指定なし」「のみ」「以外」） |
| 界隈曲の種類・ネタ曲のラジオボタン（未指定） | URLクエリなし | `songrange-all`・`jokerange-on`（指定なし）のラジオボタンが選択された状態で表示される |
| ラジオボタンの選択肢の文言 | GETリクエスト | 検索フォームのラジオボタンの選択肢に「表示」が含まれない |
| is_joke=True | `?is_joke=True` | context["jokerange"] = "only" |
| is_joke=only | `?is_joke=only` | context["jokerange"] = "only" |
| is_joke=False | `?is_joke=False` | context["jokerange"] = "off" |
| is_joke=off | `?is_joke=off` | context["jokerange"] = "off" |
| is_joke=all | `?is_joke=all` | context["jokerange"] = "on" |
| is_joke=on | `?is_joke=on` | context["jokerange"] = "on" |
| is_original/is_inst/is_questionable/is_special/is_collab/is_lack/is_deleted | 各フィールドに `True` / `False` | 対応 context フィールドが "True" / "False" |
| is_subeana経由の絞り込み(タグリンク等)は保存設定cookieを上書きしない | `is_saved_select=on`, `search_songrange=subeana` (cookie), `?is_subeana=xx` | context["songrange"] = "xx"（表示のみ反映）、`search_songrange` cookieは上書きされない |
| is_joke経由の絞り込み(タグリンク等)は保存設定cookieを上書きしない | `is_saved_select=on`, `search_jokerange=on` (cookie), `?is_joke=only` | context["jokerange"] = "only"（表示のみ反映）、`search_jokerange` cookieは上書きされない |
| songrangeクエリ(検索フォーム経由)は引き続きcookieに保存される | `is_saved_select=on`, `?songrange=xx` | `search_songrange` cookieに "xx" が保存される |
| 検索フォームの初期表示（デフォルト） | URLクエリなし | context["search_form"] = "keyword"、キーワードのラジオボタンが選択され、他のフォームは `hidden` |
| 検索フォームのラジオボタンは必ず1つ選択される | URLクエリなし・各フォームのURLクエリ | `name="search-form"` のラジオボタンが常に1つだけ選択される（JSはこれを前提にしている） |
| 全てのフォームにURLクエリが対応づけられている | GETリクエスト | 18個のラジオボタンの並びが `SEARCH_FORM_QUERIES` のキーの並びと一致する |
| 真偽値のフィルタの不正な値 | `?is_lack=foo` | 「未完成」のフォームが表示され、「指定なし」のラジオボタンが選択される |
| mediatypesのURLクエリ | `?mediatypes=youtube,nicovideo,unknown` | URLのフォームが表示され、YouTube・ニコニコ動画のチェックボックスのみ選択される（存在しないメディアは無視） |
| mediatypes未指定 | URLクエリなし | メディアのチェックボックスは選択されない |
| 検索フォームの初期表示（URLクエリ指定） | `?title=テスト` `?mediatypes=youtube` `?view_gte=100` `?is_subeana=xx` `?jokerange=off` `?is_original=True` `?is_inst=True` `?is_questionable=True` `?is_special=True` `?is_collab=True` `?is_lack=True` `?sort=-view` など | URLクエリを含むフォーム（title/url/youtube/subeana/joke/original/inst/questionable/special/collab/lack/sortなど）が表示される |
| 検索フォームの初期表示（複数指定） | `?is_lack=True&keyword=テスト` / `?title=テスト&sort=-view` / `?title=テスト&view_gte=100` / `?view_gte=100&lyrics=テスト` | ラジオボタンの並び順で先の "keyword" / "sort" / "youtube" / "lyrics" が表示される |
| ラジオボタンの並び順 | GETリクエスト | よく利用するため、先頭からキーワード・並び替え・歌詞・YouTubeの順に並ぶ（全18個） |
| 検索フォームの初期表示（空の値） | `?title=` | "keyword" が表示される |
| デフォルト値のラジオボタンに`data-default` | GETリクエスト | フィルタバッジは`data-default`のラジオボタンをデフォルト値として判定するため、各フィルタで1つだけ付き、`songrange`・`jokerange` は `COOKIE_FORMS` のデフォルト値、真偽値のフィルタは `""`（指定なし）のラジオボタンに付く |
| cookieの不正な値 | `search_songrange`・`search_jokerange`・`search_sort` に不正な値 (cookie) | デフォルト値（`all`・`on`・`-post_time`）のラジオボタンが選択される |
| 並び替えのラジオボタン | `?sort=-view` | `select` ではなく `SORT_CHOICES` の数のラジオボタンが表示され、`-view` のみが選択される |
| 並び替えのラベル | GETリクエスト | 「登録日/早い順」のように短く、YouTube関連の並び替え（`YOUTUBE_SORTS`）のみ文言の前にYouTubeのアイコンが付く（「YouTubeの」等の文言は含まない）。高評価数の後に「模倣元の数」「模倣曲の数」（#542）、最後に「ランダム」が並ぶ |
| 模倣元の数・模倣曲の数の並び替えのアイコン（#542） | GETリクエスト | `imitate_count`・`-imitate_count` は `fas fa-sitemap imitate`（上下反転）、`imitated_count`・`-imitated_count` は `fas fa-sitemap` のアイコンで、それぞれ「模倣元の数/少ない順」等のラベルが表示される |
| 並び替えのデフォルト | URLクエリなし | `-post_time`（更新日が遅い順）が選択される |
| YouTube関連のクエリをJSに渡す | GETリクエスト | context["youtube_queries"] が `query_utils` の `YOUTUBE_FILTERS`・`YOUTUBE_SORTS` と一致し、`json_script`（`#youtube-queries`）で出力される |
| ラジオボタンを全て表示するボタン | GETリクエスト | `#search-form-radios-toggle`（`aria-controls="search-form-radios"`、`aria-expanded="false"`、「全て表示」）が表示される |
| フォームボタンの設定のデフォルト（#1164） | `form_button`クッキーなし | `#search-form-radios`は`<div class="radio-group" id="search-form-radios">`（アイコンと文字） |
| フォームボタンの設定がアイコンのみ（#1164） | `form_button=icon` | context["form_button"] = "icon"、`#search-form-radios`のみに`icon-only`クラスが付き、並び替え等のフォーム内のラジオボタンには付かない |
| フォームボタンの設定のcookieの不正な値（#1164） | `form_button=text` | context["form_button"] = "icon_text"（デフォルト）にフォールバックし、`icon-only`クラスは付かない |
| 「結果を表示」ボタンの廃止（#970） | GETリクエスト | `scroll-to-results` が含まれない |

#### 7-3. `SongView` (`/songs/<id>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲ID | 有効なsong_id | HTTP 200 |
| 存在しない曲ID | 無効なsong_id | HTTP 404 |
| 削除済み曲 | `is_deleted=True` の曲 | HTTP 404 または特定の表示 |
| is_questionable=True の曲 | `is_questionable=True` の曲 | レスポンスに「界隈曲?」タグが含まれる |
| is_questionable=False の曲 | デフォルトの曲 | レスポンスに「界隈曲?」タグが含まれない |
| デフォルトの曲 | `is_questionable=False`, `is_limited=False` | レスポンスに `<meta name="robots">` が含まれない |
| is_questionable=True の曲 | `is_questionable=True` の曲 | レスポンスに `<meta name="robots" content="noindex, nofollow">` が含まれる |
| is_limited=True の曲 | `is_limited=True` の曲 | レスポンスに `<meta name="robots" content="noindex, nofollow">` が含まれる |

#### 7-4. `SongNewView` (`/songs/new/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| GETアクセス | GETリクエスト | HTTP 200、フォームが表示される |
| POST: YouTube以外のURL | `url="https://example.com/..."` | HTTP 200、"YouTube" を含むエラー |
| POST: YouTube APIの呼び出しに失敗（#1146） | YouTubeのURL・`get_youtube_api` が `YoutubeApiError` を送出 | 500エラーにならずHTTP 200でエラーを表示し、Songは作成されない（動画が削除・非公開の場合と同様に扱う） |
| POST: 作者が空白 | `url=""`, `authors="  "` | HTTP 200、"作者" を含むエラー |
| POST: タイトルが空 | `url=""`, `authors="テスト作者"`, `title=""` | HTTP 200、"タイトル" を含むエラー |
| POST: タイトルが`Song.title`のmax_length超（#1085） | `title`がmax_length+1文字 | HTTP 200、"タイトル" を含むエラー、Songは作成されない（フォームを経由せず保存するため直接バリデーションが必要） |
| POST: 作者名が`Author.name`のmax_length超（#1085） | `authors`がmax_length+1文字 | HTTP 200、"作者名" を含むエラー、Songは作成されない |
| POST: is-questionable時、オリジナル模倣は強制OFF・その他フラグの入力値はそのまま保存される | `is-questionable-manual=on`, `is-original-manual=on`, `is-subeana-manual=on` | 保存されたSongの `is_questionable=True`、`is_original=False`、`is_subeana=True` |
| POST: 作者名がpast別名と一致し統一した名義へ正規化される（#1029、#1137） | `authors=`past別名のname | 保存後、redirect先URLに`name_unified=1`が付与される |
| POST: 正規化が発生しない | `authors=`通常の作者名 | redirect先URLに`name_unified`は付与されない |

#### 7-5. `SongEditView` (`/songs/<id>/edit/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲のGET | 有効なsong_id | HTTP 200 |
| 存在しない曲のGET | 無効なsong_id | HTTP 404 |
| GET: ブラウザにキャッシュさせない（#1135） | 有効なsong_id | `Cache-Control`に`no-store`が含まれ、`public`は含まれない（キャッシュされた古いフォームの送信で、その間の編集が巻き戻るのを防ぐ） |
| POST: is_questionable時に歌詞・模倣・下書き・オリジナル模倣が強制的に空/OFF | `is_questionable=True`, `lyrics="..."`, `imitate="<id>"`, `is_draft=True`, `is_original=True` | 保存されたSongの `lyrics=""`、`imitates`が空、`is_draft=False`、`is_original=False`、`is_questionable=True` |
| POST: is_questionable時も非公開/削除済み・ネタ曲・インスト・すべあな界隈曲は保存される | `is_questionable=True`, `is_deleted=True`, `is_joke=True`, `is_inst=True`, `is_subeana=True` | 各フラグがそれぞれ `True` のまま保存される |
| POST: 作者名が`Author.name`のmax_length超（#1085） | `authors`がmax_length+1文字 | HTTP 200、"作者名" を含むエラー |
| POST: 作者名がpast別名と一致し統一した名義へ正規化される（#1029、#1137） | `authors=`past別名のname | 保存後、redirect先URLに`name_unified=1`が付与される |
| POST: 正規化が発生しない | `authors=`通常の作者名 | redirect先URLに`name_unified`は付与されない |

#### 7-6. `ContactView` (`/contact/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| GETアクセス | GETリクエスト | HTTP 200 |
| POST: 正常な入力 | `category="不具合の報告"`, `detail="..."` | HTTP 200、`context["result"] == "ok"` |
| POST: 不正な入力 | `detail` 未入力 | HTTP 200、`context["result"]` にエラーメッセージ |

#### 7-7. `SongDeleteView` (`/songs/<id>/delete/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲のGET | 有効なsong_id | HTTP 200 |
| 存在しない曲のGET | 無効なsong_id | HTTP 404 |
| POST: 正常な削除理由 | `reason="..."` | `/songs/<id>?toast=delete` へリダイレクト |
| POST: 削除理由が空 | `reason=""` | HTTP 200、`context["error"]` にエラーメッセージ |

#### 7-8. `AuthorView` (`/authors/<id>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する作者ID | 有効なauthor_id | HTTP 200 |
| 存在しない作者ID | 無効なauthor_id | HTTP 404 |
| 別名なし (#992) | 別名未登録 | 別名一覧への導線は表示されるが「件の別名」は表示されない |
| 正方向の別名あり (#992) | 別名を1件登録 | 「1件の別名」が表示される |
| 逆方向の別名あり (#992) | 他authorが自分のnameと一致する別名を保持 | 「1件の別名」が表示される（正方向＋逆方向の合計） |
| 推移的な件数 (#1007) | `past`で1ホップ先の別名がさらに`spell`の別名を持つ（2ホップ） | 「2件の別名」が表示される（`get_transitive_aliases()`の件数に合わせる） |
| 別名ボタンのアイコン (#1024) | 正常アクセス | `fa-people-arrows`アイコンが含まれる |
| 統計ボタンのリンク (#334) | 正常アクセス | `/authors/<id>/stats/` へのリンクが含まれる |
| 統計ボタンのアイコン (#334) | 正常アクセス | `fa-chart-line`アイコンが含まれる |
| 統計ボタン下のメッセージ (#334、#968で鍵歴表示に変更。#1099でpt表示に変更) | 曲にview=1234を設定 | 鍵歴(`context["kenreki"]["points"]`、1234は7段階到達で7pt）がそのまま表示される（鍵盤数(7//2=3)には変換しない） |
| 統計ボタン下のメッセージの非表示 (#968) | authorに曲が1件も無い | `#author-stats-summary`自体が表示されない（`context["kenreki"]`が`None`） |

#### 7-8-1. `AuthorAliasesView` (`/authors/<id>/aliases`)（#992、#1007、#1024）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 別名なし | 別名未登録のauthor | HTTP 200、「別名が見つかりませんでした」 |
| 正方向の別名 | 別名を1件登録 | 別名名が表示され、編集・削除リンクが含まれる |
| 逆方向の別名 | 他authorが自分のnameと一致する別名を保持 | 相手authorの名前が表示されるが、編集・削除リンクは含まれない |
| `alias_type=past`かつ対象authorが実在 | 別名nameと同名のAuthorが存在 | `channel/<name>/`へのリンクが含まれる |
| `alias_type=past`だが対象authorが不在 | 別名nameと同名のAuthorが存在しない | `channel/<name>/`へのリンクが含まれない |
| `alias_type`がpast/another以外 | 例: `abbr`。対象authorは実在 | `channel/<name>/`へのリンクが含まれない |
| 別名に`/`を含む（回帰、#1127） | `alias_type=past`、別名`別名/スラッシュ`と同名のAuthorが存在 | `NoReverseMatch`にならずHTTP 200、`channel/<name>/`へのリンクが含まれる |
| 再読み込みボタン (#996) | 正常アクセス | `reloadPage()`呼び出しと`fa-redo`アイコンが含まれる |
| 追加ボタンのアイコン (#996) | 正常アクセス | `fa-plus`アイコンが含まれる |
| `alias_type=past`・正方向のラベル (#1019) | 自分がpastの別名を登録 | 「以前の名称」と表示される |
| `alias_type=past`・逆方向のラベル (#1019) | 他authorが自分をpastの別名として登録 | 「その後の名称」と表示される |
| 逆方向の別名の遷移アイコン | 他authorが自分のnameと一致する別名を保持 | 編集できない代わりに、相手authorの別名一覧への遷移アイコン(`fa-arrow-right`)が表示される |
| 遷移先author idが0の場合の遷移アイコン | 遷移先authorを`id=0`で作成 | テンプレートが`is not None`で判定しているため、`id=0`でも遷移アイコンが表示される（真偽値判定だと0がfalsyになり表示されなくなる） |
| 名義を統一するフォームの初期状態（#1029、#1137） | past別名が存在するauthorのGET | 「[ ] 以前の名称 ↓ [x] 現在の名義」の順に並び、`#unify-name-submit`ボタンは`disabled`ではなくラベルは「統一する」（フォームを変更しなくても統一できる。詳細は7-8-5） |
| 作者ページへの導線（#1024） | 正常アクセス | 作者自身のページ（`/authors/<id>/`）へのリンク（`href`属性完全一致で判定。`/authors/<id>/aliases/...`系の他リンクとの部分一致による誤検出を避けるため）が表示される |
| 作者ページボタンの位置（#1024） | 正常アクセス | `.action-buttons`内で「再読み込み」「別名を追加する」より前（DOM順で最初、一番左）に配置される |

##### 推移的関係解決の反映・遷移アイコン（#1007、#1019）

#1003・#1005の具体例（名義Aに別名義B・以前の名称C・以前の名称D・グループEを登録）を再現し、各authorの一覧画面が仕様表の通りになることを確認する。

遷移アイコン(`fa-arrow-right`)の遷移先は以下の優先順位で決定する。表示位置は編集アイコン(`fa-pen`)の左。

1. 別名自体(`row.name`)に対応する実在Authorがあれば、そのAuthorの一覧画面（編集可能・不可を問わず優先）
2. 対応するAuthorがなければ、そのAuthorAlias自体を実際に所有しているauthor（`source.author`、必ず実在する）の一覧画面へのフォールバック
3. 遷移先が現在表示中のページ自身の場合は表示しない
   - 編集可能な行（自分が直接保有する別名）でAuthorが対応しない場合、フォールバック先(`source.author`)は常に自分自身になるため、この条件で結果的に非表示になる（「フォールバックしても意味がない」を専用の分岐ではなくこのチェックで実現している）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| Aの一覧 | `A.get_transitive_aliases()`を表示 | B(別名義)・C(以前の名称)・D(以前の名称)・E(所属グループ)の4件が表示され、いずれも編集・削除リンクを含む（直接保有）。B/C/D/Eはいずれも実在するため、編集アイコンに加えてそれぞれの一覧画面への遷移アイコンも表示される |
| Bの一覧 | 同上 | Aのみ表示される（`another`は中継点にならないためC/D/Eは表示されない）。編集・削除リンクは含まれない（逆方向）が、Aは実在するため遷移アイコンが表示される |
| Cの一覧 | 同上 | A（その後の名称）・B・D（以前の名称）・Eが表示される（`past`経由でAを介して推移的に到達）。いずれも編集・削除リンクは含まれない（自分が直接保有する別名ではない）が、A・B・D・Eいずれも実在するためそれぞれへの遷移アイコンが表示される |
| Eの一覧 | 同上 | Aのみ表示され、ラベルは「所属している名義」（`group`は中継点にならないためB/C/Dは表示されない）。編集・削除リンクは含まれないが、Aは実在するため遷移アイコンが表示される |
| グループラベルの出し分け | 同上 | Aの一覧ではEの関係が「所属グループ」、Eの一覧ではAの関係が「所属している名義」と表示される |
| 対応するAuthorが不在の別名のフォールバック | pがghost(past、Author不在)とr(past、Author実在)の別名を持ち、rの一覧を表示 | pへの関係は直接だが逆方向で編集できず、pは実在するため遷移アイコンが表示される。一方ghostへの関係は間接的で対応する実在Authorがないため、フォールバックとして所有者p自身の一覧画面への遷移アイコンが表示される（結果としてpの一覧へのリンクが2件表示される） |

##### 遷移先author idの補完クエリの範囲（#1023）

`AuthorAliasesView`は`TransitiveAlias.author_id`（#1023で追加。`get_transitive_aliases()`が追加クエリなしに解決した範囲でのみ設定される）を優先して使い、`author_id`が`None`の行（正方向かつ`another`/`group`のリーフエッジ）に限定して補完的にAuthorを問い合わせる。この対象はクラスタ全体ではなく未解決の名前のみのため、クラスタが大きくなっても補完クエリのIN句が際限なく大きくなることはない。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| クエリ数の回帰防止 | Cの一覧を表示（A・Dはauthor_id解決済み、B・Eは未解決） | ビューの総クエリ数が想定通り（9件）に収まる |
| 補完クエリの対象範囲 | 同上 | 補完クエリのIN句にB・Eの名前のみが含まれ、解決済みのA・Dの名前は含まれない |

#### 7-8-2. `AuthorAliasNewView` (`/authors/<id>/aliases/new`)（#992）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 正常なPOST | 有効な`name`・`alias_type` | AuthorAliasが作成され一覧画面へリダイレクト |
| 正常なPOST | 上記 | `History.create_for_author()`が呼ばれ、`history_type="new"`のレコードが作成される |
| nameが重複 | 既存のname | HTTP 200のままエラー表示、レコードは作成されない |
| nameがauthor自身と同じ | `name=author.name` | HTTP 200のままエラー表示、レコードは作成されない |
| Discord通知 | 正常なPOST | `send_discord()`がNEW_DISCORD_URL宛に、別名名・作者名を含む内容で呼ばれる |
| Discord通知失敗 | `send_discord()`が`False`を返す | HTTP 500。DB書き込み前に通知するため、AuthorAliasは作成されず、孤立したHistoryも作成されない |
| TOCTOU（重複チェックのすり抜け） | `AuthorAliasForm.clean_name`をモックして重複チェックをバイパスし、既存nameでPOST | DB制約(IntegrityError)を捕捉し、HTTP 200のままフォームエラー表示（500にならない）。レコードは重複作成されない |
| `alias_type`のプレースホルダー (#996) | GETリクエスト | `<option value="" selected disabled>選択してください</option>`が含まれる |
| `alias_type`の説明属性 (#996) | GETリクエスト | 各`<option>`に`data-description`属性が付与されている |
| 登録ボタンの初期状態 (#996) | GETリクエスト | `<input type="submit" ... disabled>`（フォームがinvalidな状態で初期表示される） |
| author_alias_form.jsの読み込み (#996) | GETリクエスト | スクリプトタグが含まれる |
| `group`選択肢 (#1004) | GETリクエスト | `value="group"`の選択肢（「グループ」）が含まれる |
| 別名義(another)の説明文 (#1004) | GETリクエスト | 「公認」の旨が含まれる |
| 以前の名称(past)の説明文 (#1029、#1137) | GETリクエスト | 名義の統一先として選択できる旨（「名義を統一する」）が含まれる |

#### 7-8-3. `AuthorAliasEditView` (`/authors/<id>/aliases/<alias_id>/edit`)（#992、#1024）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| ブラウザにキャッシュさせない（#1135） | GETリクエスト | `Cache-Control`に`no-store`が含まれ、`public`は含まれない（SongEditViewと同様） |
| 存在しないalias_id | 無効なalias_id | HTTP 404 |
| 他authorが所有するalias_id | 別authorのalias_idを指定 | HTTP 404 |
| 正常なPOST | 有効な`name`・`alias_type` | AuthorAliasが更新され一覧画面へリダイレクト |
| 正常なPOST | 上記 | `History.create_for_author()`が呼ばれ、`history_type="edit"`のレコードが作成される |
| 自分自身の現在のnameのまま更新 | `name`を変更しない | 重複エラーにならず更新される |
| 他のaliasのnameと重複 | 同一author内の他のalias.name | HTTP 200のままエラー表示、更新されない |
| 実質的な変更なし | `name`・`alias_type`とも変更しない値でPOST | リダイレクトはするが`History`は作成されず、Discord通知も送られない（SongEditViewと同様） |
| Discord通知 | 実質的な変更があるPOST | `send_discord()`がNEW_DISCORD_URL宛に、変更後の内容を含む形で呼ばれる |
| Discord通知失敗 | 変更ありのPOSTで`send_discord()`が`False`を返す | HTTP 500。DB書き込み前に通知するため、AuthorAliasは更新されず（元の値のまま）、Historyも作成されない |
| TOCTOU（重複チェックのすり抜け） | `AuthorAliasForm.clean_name`をモックして重複チェックをバイパスし、既存nameでPOST | DB制約(IntegrityError)を捕捉し、HTTP 200のままフォームエラー表示（500にならない）。更新前の値のまま維持される |
| 現在のalias_typeが選択済み (#996) | GETリクエスト | 該当する`<option>`に`selected`が付与されている |
| `alias_type`のプレースホルダー (#996) | GETリクエスト | `<option value="" disabled>選択してください</option>`が含まれる（selectedではない） |
| author_alias_form.jsの読み込み (#996) | GETリクエスト | スクリプトタグが含まれる |
| 別名一覧画面へ戻るボタン (#1024) | GETリクエスト | 別名一覧画面（`/authors/<id>/aliases/`）へのリンク（`href`属性完全一致で判定。このページ自体のフォームaction`/authors/<id>/aliases/<alias_id>/edit/`との部分一致による誤検出を避けるため）と「戻る」の文言が含まれる |
| 更新ボタンのスタイル (#1024、#450) | GETリクエスト | 更新ボタンが名義の統一の確認画面と同様の`action-button`形式（`<button type="submit" class="action-button black-action-button">`）で「更新する」と表示され、「戻る」ボタンと同じ`.action-buttons`内に並ぶ。幅は共通の`.action-button`（`box-sizing: content-box`）で「戻る」と同じ140pxになるため、幅指定用のクラスは付けない |

#### 7-8-4. `AuthorAliasDeleteView` (`/authors/<id>/aliases/<alias_id>/delete`)（#992）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200、削除確認内容が表示される |
| 存在しないalias_id | 無効なalias_id | HTTP 404 |
| 正常なPOST | POSTリクエスト | AuthorAliasが削除され一覧画面へリダイレクト |
| 正常なPOST | 上記 | `History.create_for_author()`が呼ばれ、`history_type="delete"`、`history.author`は削除後も維持される |
| Discord通知 | 正常なPOST | `send_discord()`がNEW_DISCORD_URL宛に、削除対象の別名名を含む内容で呼ばれる（新規・編集と同じ通知先） |
| Discord通知失敗 | `send_discord()`が`False`を返す | HTTP 500。AuthorAliasは削除されず、Historyも作成されない（通知できた場合のみ実削除する設計） |
| キャンセル・削除ボタンのアイコン (#996) | GETリクエスト | `fa-times`・`fa-trash-alt`アイコンが含まれる |

#### 7-8-5. `AuthorUnifyNameSetView` (`/authors/<id>/aliases/unify`)（#1008, #1029, #1137）

候補の名義（`Author.name` + `alias_type="past"`の別名）と同名のAuthorに紐づくSongを、選択した名義のAuthor（統一先）へ全て移す。曲を移したAuthor自体は削除せず、曲数が0になるだけ（#1137で削除を廃止）。

統一先は、選択した名義と同名の既存Authorがあればそれ、なければauthor自身。

- author自身が統一先で、以前の名称を選択した場合: `Author.name`と選択したAuthorAlias.nameを入れ替える。Song.authorsはAuthorのPK参照のため、元々authorに紐づく曲はSongデータを変更せずに表示上の作者名が変わる
- 既存の別Authorが統一先の場合: `Author.name`はuniqueでauthorをその名前に変更できないため、authorのSongに加えてAuthorAlias・AuthorLinkも統一先へ移し、authorの旧名を統一先の`past`別名として登録する

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 現在の名前を選択し、移す曲もない | `name=author.name`、以前の名称と同名のAuthorが曲を持たない | 何も変更されず`?toast=unify_noop`付きで一覧画面へリダイレクト。Discord通知・Historyの作成も行わない |
| 現在の名前を選択（フォーム未変更での統一、#1137） | `name=author.name`、以前の名称と同名の別AuthorがSongを持つ | そのSongがauthorに付け替わり、`?toast=unify`付きでリダイレクト。別Authorは削除されず曲数0で残る。`Author.name`は変わらない |
| past別名を選択 | `name=`past別名のname（同名のAuthorは不在） | `Author.name`が入れ替わる。選ばれた側のAuthorAlias行は削除され、旧名が新たな`past`別名として再登録される。`?toast=unify`付きでリダイレクト |
| 他の以前の名称のAuthorの曲も統一 | 選択していない別のpast別名と同名のAuthorがSongを持つ | そのSongも統一先に付け替わり、そのAuthorは曲数0で残る |
| past以外の種別の別名と同名のAuthorは対象外 | `another`別名と同名のAuthorがSongを持つ | そのSongは付け替えられない（意図的に区別すべき名義のため） |
| `alias_type`がpast以外の別名を選択 | `name=`another等の別名のname | 変更されず、`?toast=unify_error`付きでリダイレクト |
| 既存のAuthorと同名のpast別名を選択 | 別Author（統一先）が同名で実在し、author側もSong・AuthorLink・AuthorAliasを持つ | authorのSong・AuthorLink・AuthorAliasが全て統一先に付け替わる。選択したpast別名は削除され、旧名が統一先の`past`別名として登録される。authorは削除されず（名前もそのまま）曲数0で残る。統一先の別名一覧へ`?toast=unify`付きでリダイレクト |
| 統一先が旧名と同名の別名を既に保有 | 統一先のAuthorAlias.name == old_name | その別名をそのまま活かし、`old_name`のAuthorAliasが重複登録（IntegrityError）されない。他のpast別名と同様に選択候補になるよう`alias_type`が`"past"`へ更新される |
| 統一先が同じグループ名を既に保有 | author・統一先の双方が同名の`group`別名を持つ | `(name, author)`のunique制約に抵触しないよう、author側のものは移さずに削除され、統一に成功する |
| 統一による曲の編集履歴記録（#1034） | 統一先が既存の別Authorで、authorが複数のSongを持つ | 付け替わった各Songの編集履歴一覧（`History.get_for_song(song)`）に、`title="名義の統一により作者を統合"`・`history_type="edit"`・`changes`に`["作者", "id=<移動元.id>, name=<移動元.name>", "id=<統一先.id>, name=<new_name>"]`を含むレコードが1件ずつ作成される。移動元と統一先が同名になる場合もあるため、idを含めて実体が変わったことを明示している。`History.objects.bulk_create()`でまとめて作成するため曲数分のクエリにはならない。無関係なSongの編集履歴は増えない |
| 名前の変更による曲の編集履歴記録（#1034） | 統一先がauthor自身で、past別名を選択 | 元々authorに紐づいていた各Songの編集履歴一覧にも、`title="名義の統一により作者名を変更"`・`changes`に`["作者", old_name, new_name]`を含むレコードが作成される |
| 統一曲・名前変更曲が同時に存在するケース（#1034） | 別のpast別名のAuthorのSong（統一側）と、元々authorに紐づくSong（名前変更側）が両方存在 | 両方の曲にそれぞれ正しい`title`で編集履歴が1件ずつ作成される |
| 統一前から双方に紐づく曲の重複排除（#1034） | あるSongが統一前からauthorと移動元のAuthor双方の共著 | 編集履歴は統一側の1件のみ作成され、Songの作者はauthorのみになる |
| 統一先・移動元の作者の編集履歴 | 名前の変更あり、別のpast別名のAuthorがSongを持つ | 統一先の`History`は`title="名義を『<new_name>』に統一"`・`history_type="edit"`で、`changes`に`["名義", 旧名, 新名]`と`["統一した作者", "id=<移動元.id>, name=...", "id=<統一先.id>, name=<new_name>"]`が含まれる。移動元のAuthorは削除されずに残るため、そちらの編集履歴一覧にも同じtitleで自身の`["統一した作者", ...]`行のみを含むレコードが作成される |
| 曲を持たないAuthorは統一した作者として記録しない | 以前の名称と同名のAuthorが曲を持たない | 統一先の`changes`に`["統一した作者", ...]`行は含まれず、そのAuthorの編集履歴も作成されない（何も変わらないため） |
| 移動元の作者の過去のHistoryは維持 | 移動元のAuthorに紐づく既存のHistoryが存在 | 統一実行後もそのHistoryの`author`・`title`等は変わらない（#1137でAuthorの削除を廃止したため、`on_delete=SET_NULL`でNULLになることもない） |
| 統一対象の曲数が多い場合のクエリ数 | 移動元のAuthorが1件/5件のSongを持つ | idでまとめて付け替え、編集履歴も`bulk_create()`するため、曲数を増やしてもクエリ数が変わらない |
| Discord通知 | 正常なPOST | `send_discord()`がNEW_DISCORD_URL宛に、変更前後の名前を含む内容で呼ばれる |
| Discord通知（統一元あり） | 以前の名称と同名のAuthorがSongを持つ | 通知内容に統一元のAuthorのid（`Author(id=...)`）が含まれる |
| Discord通知失敗 | `send_discord()`が`False`を返す | HTTP 500。`Author.name`・選択されたAuthorAlias行・Songの作者はいずれも変更されず、Historyも作成されない（通知成功後にDB確定するパターン） |
| Discord通知待機中の並行削除（TOCTOU、選択した別名） | `send_discord()`の完了待ち中に対象のpast別名が別リクエストで削除されたと仮定 | `AuthorAlias.DoesNotExist`が未処理の例外(500)にならず、`?toast=unify_error`へ穏当にリダイレクトされる。`Author.name`は変更されない |
| Discord通知待機中の並行削除（TOCTOU、統一先の既存Author） | `send_discord()`の完了待ち中に統一先の既存Authorが別リクエストで削除されたと仮定 | 統一先を再取得し、author自身の名前を変更する通常の統一として`?toast=unify`付きで成立する |
| Discord通知待機中の無関係な別名作成（TOCTOU） | `send_discord()`の完了待ち中に、無関係な別authorがold_nameと同名の`AuthorAlias`を新規作成したと仮定 | 所有者を確認できないため再利用せず安全側に倒し、曲の付け替え・別名の移動を含む統一全体をロールバックして`?toast=unify_error`へリダイレクトする。無関係な別名のalias_typeは書き換えられない |
| 旧名(old_name)が既存の別名と衝突 | old_nameと同名の`AuthorAlias`をauthor・統一先以外の別authorが既に保有（「逆方向」の関係として正常にありうる状態） | `AuthorAlias.name`のグローバルなunique制約により再登録が決定的に失敗するため、Discord通知を送る前に検知して`?toast=unify_error`へリダイレクトする。`send_discord()`は呼ばれない |
| 別名一覧画面のフォーム表示 | authorが`alias_type="past"`の別名を持つ | フォーム（`#unify-name-form`）と「名義を統一する」の見出し、チュートリアルアイコン（`data-tutorial="unify-name"`、#1126でインラインのonclickから変更）が表示される。フォームの送信先は確認画面（`AuthorUnifyNameConfirmView`） |
| 別名一覧画面のフォーム非表示 | authorが`alias_type="past"`の別名を持たない | フォームは表示されない（選択肢が現在の名前1件のみのため） |
| フォームの並び（#1137） | authorが`alias_type="past"`の別名を持つ | 「[ ] 以前の名称 ↓ [x] 現在の名義」の順に、past別名・矢印（`#unify-name-arrow`）・現在の名義が並び、初期状態では現在の名義のみが`checked`になる。選択を変えると、選択した名義が矢印の下へ移動する（JSによるDOM操作のため手動確認） |
| 統一するボタン（#1137） | authorが`alias_type="past"`の別名を持つ | `#unify-name-submit`ボタンは`disabled`ではなく（フォームを変更しなくても統一できる）、ラベルは「統一する」 |

#### 7-8-6. `AuthorUnifyNameConfirmView` (`/authors/<id>/aliases/unify/confirm`)（#1029, #1137）

名義の統一前に内容を確認させるための画面。統一により他のAuthorの曲が統一先へ移ることをIPベースの匿名編集者でも実行できてしまうため、実際の統一前にワンクッション挟む安全策。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 無効な名義 | 候補にない`name` | 確認画面を表示せず`?toast=unify_error`付きで別名一覧へリダイレクト |
| 現在の名前を選択し、移す曲もない | `name=author.name`、移す曲がない | 確認画面を表示せず`?toast=unify_noop`付きで別名一覧へリダイレクト |
| 現在の名前を選択し、移す曲がある（#1137） | `name=author.name`、以前の名称と同名の別AuthorがSongを持つ | そのSongのタイトルが箇条書きで表示された上で「の作者が『現在の名義』に統一されます」と続き、「作者『<名前>』の曲は全て『現在の名義』に移動します」が表示される。作者のidと「作者自体は削除されません」は表示されない |
| 統一先が既存のAuthorでない確認画面 | 選択したpast別名と同名のAuthorが存在しない | 「既存の作者」「に移動します」の文言は表示されない |
| 統一先が既存のAuthorの確認画面 | 選択したpast別名と同名のAuthorが存在 | 「既存の作者『<名前>』が統一先となり、この作者の曲・別名・作者リンクは全てそちらに移動します」が表示される。統一先のidと「この作者自体は削除されません」は表示されない |
| 対象曲がない場合の表示 | 表示上の作者名が変わるSongがない | 「名義が『新名』に統一されます」という文のみ表示される |
| 対象曲の一覧表示 | 名前の変更あり、authorがSongを持つ | 各Songのタイトルが箇条書きで表示された上で「の作者が『新名』に統一されます」と続く |
| 統一先の既存Authorの曲は一覧に含めない | 統一先の既存Author・authorの双方がSongを持つ | authorのSongは一覧に含まれるが、統一先のSongは表示上の作者名が変わらないため含まれない |
| 共著曲は重複表示されない | 同じSongが統一対象の複数のAuthorの共著になっている | そのSongタイトルは箇条書きに1回だけ表示される（`distinct()`によるSong単位の重複排除） |
| 曲が10件以下の場合 | Songが10件以下 | 「全て表示」ボタン（`#unify-name-show-all-songs`）は表示されず、全曲が表示された状態になる |
| 曲が11件以上の場合 | Songが11件以上 | 11件目以降が`class="unify-name-song-hidden"`で非表示になり、「全て表示」ボタンが表示される |
| 統一するボタンのラベル・要素・送信先 (#450) | 確認画面の表示 | ボタンのラベルは「統一する」（「変更する」は含まれない）、`<button type="submit" class="action-button black-action-button">`で、幅指定用のクラスは付かない（共通の`.action-button`で「戻る」と同じ幅になる）。送信先は`AuthorUnifyNameSetView` |
| データを変更しない | GETリクエストのみ | `Author`・`AuthorAlias`・Songの作者等のデータは一切変更されない |

#### 7-9. `ChannelView` (`/channel/<name>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する作者名 | 有効なchannel_name | `/authors/<id>/` へリダイレクト (HTTP 302) |
| 存在しない作者名 | 無効なchannel_name | HTTP 404 |
| 作者名に`/`を含む（回帰、#1127） | `スラッシュ/作者` | URLコンバータが`path`のため`reverse`でき、`/authors/<id>/`へリダイレクトされる |

#### 7-10. `HistoriesView` (`/histories/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| author向けHistory (#991) | `History.create_for_author()`で作成したHistoryが存在 | 作者名・作者ページへのリンクが表示され、「この曲は削除されました」は表示されない |
| author削除後のHistory (#991) | 上記のauthorを削除 | 「この曲または作者は削除されました」が表示される |

#### 7-10-1. `EditorView` (`/editor/<id>/`)（#991でauthor向けHistory表示を追加）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在するeditor | 有効なeditor_id | HTTP 200 |
| author向けHistory | `History.create_for_author()`で作成したHistoryが存在 | 作者名が表示され、「この曲は削除されました」は表示されない |

#### 7-11. `SongCardsView` (`/api/html/song_cards`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| `sort=upload_time` | GETリクエスト | HTTP 200、「YouTubeの曲を表示しています」が含まれる |
| `sort=-upload_time` | GETリクエスト | HTTP 200、「YouTubeの曲を表示しています」が含まれる |
| ソート指定なし | GETリクエスト | 投稿日用のsearch-infoが含まれない |
| `sort=title` | GETリクエスト | 投稿日用のsearch-infoが含まれない |
| `is_questionable=True` の曲 | GETリクエスト | カードHTMLに `song-card-lyrics` が含まれない |
| `is_questionable=False` の曲 | GETリクエスト | カードHTMLに `song-card-lyrics` が含まれる |
| エラーメッセージのエスケープ（#1126） | `sort=<img src=x onerror=alert(1)>` | `class='error'` の要素内で入力値がHTMLエスケープされ、`<img` が含まれない |
| `is_questionable=True` / `False` | GETリクエスト | 「界隈曲?が有効です」が含まれる |
| `is_special=True` / `False`（#939） | GETリクエスト | 「スペシャルデザインが有効です」が含まれる |
| `is_special=True` の絞り込み（#939） | `is_special=True` の曲と通常の曲が存在 | スペシャルデザインの曲のカードのみが返される |
| `is_collab=True` / `False`（#943） | GETリクエスト | 「合作が有効です」が含まれる |
| `is_collab=True` の絞り込み（#943） | 作者2人の曲と通常の曲が存在 | 合作の曲のカードのみが返される |

#### 7-11-1. `song_guessers` (`/api/html/song_guessers`)（#1126、#1124）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| エラーメッセージのエスケープ | `sort=<img src=x onerror=alert(1)>` | `class='error'` の要素内で入力値がHTMLエスケープされ、`<img` が含まれない |
| 候補の並び順（#1124） | 模倣曲の数が2・1・0・0の曲が存在、`guesser` のみ指定 | 模倣曲の数が多い順に表示され、同じ数の曲は登録日の遅い順 |
| sort指定時の並び順 | `sort=title` | 指定した並び順（タイトル順）で表示される |
| 末尾のメッセージ | 候補が51件・1件・0件 | 51件は「これ以上の候補を表示する為には条件を絞ってください。」、1件は「これ以上の検索結果はありません。」、0件は「検索結果はありません。」で始まる |

#### 7-11-2. `song_cards`・`song_guessers` のレート制限（#1188）

`@ratelimit(key='ip', rate='2/second')`でIPごとに毎秒2回までに制限する。PythonAnywhereでは`REMOTE_ADDR`がロードバランサーのIPになり、全ユーザーが1つのIPとして数えられるため、`settings.RATELIMIT_IP_META_KEY`（`lib/ip.py`の`get_client_ip`）で`X-Real-IP`（無ければ`REMOTE_ADDR`）を使う。テストクライアントの`REMOTE_ADDR`は常に同じため、`X-Real-IP`ごとに数えられていることを確認できる。制限を超えたときのレスポンスの内容（429・`Retry-After`等）は結合テスト計画書の「16. レート制限フロー」で確認するため、ここではステータスだけを確認する。1秒の区切りをまたいでカウントがリセットされないよう、`django_ratelimit.core.time`をモックして時刻を固定する。各テストは両方のビューで確認する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 1秒に3回目で制限 | 同じ`X-Real-IP`で3回GET | 2回目まではステータス200、3回目は429 |
| X-Real-IPごとに制限 | IP Aで2回GETした後、IP B・IP AでGET | IP Bは200、IP Aは429 |
| X-Forwarded-Forでは回避できない | 同じ`X-Real-IP`で`X-Forwarded-For`を毎回変えて3回GET | 3回目は429（`X-Forwarded-For`はクライアントが自由に付けられるため使わない。#1189の不一致の記録は`assertLogs`で受け取る） |
| X-Real-IPが無ければREMOTE_ADDRごとに制限 | `REMOTE_ADDR` Aで2回GETした後、`REMOTE_ADDR` B・AでGET | Bは200、Aは429 |
| X-Real-IPがIPでない | `X-Real-IP: not-an-ip`で2回GETした後、`X-Real-IP`なしでGET | 2回とも200（500にならない）で、3回目は`REMOTE_ADDR`で数えて429 |

#### 7-12. `AiView` (`/ai/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| `show_janome_notice` Cookie未指定（デフォルトTrue） | Cookie未指定 | janomeによる作成についての案内（`#janome-notice`）が表示される |
| `show_janome_notice=False` Cookie指定 | `show_janome_notice=False` | `#janome-notice`が表示されない |
| 単語入れ替え機能は提供しない（方針転換、#1053） | Word候補が存在する単語を含む歌詞 | `class="word-token"` は表示されず、歌詞はプレーンテキストのまま表示される |
| レガシーgenetype="model"は対象外（GPTインポート廃止） | `genetype="model", score=5`のレコードが存在 | 最高評価の歌詞に表示されない（`genetype="janome"`のみ対象） |

#### 7-13. `AiResultView` (`/ai/result/`)（#1053）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| Word候補がある単語 | 該当する`Word`が存在 | `class="word-token"` としてクリック可能に表示される |
| レガシーgenetype="model"は対象外（GPTインポート廃止） | `genetype="model", score=0`のレコードが存在 | 作成結果キューに表示されない（`genetype="janome"`のみ対象） |
| 未評価janomeが0件の場合のフォールバック | 未評価のjanomeレコードが無く、評価済みjanomeレコードのみ存在 | 評価済みのjanomeレコードが表示される（単語入れ替えの元歌詞が途絶えないようにするため） |
| フォールバック時もレガシーgenetype="model"は対象外 | 未評価janomeが0件で、評価済みの`genetype="model"`レコードが存在 | フォールバックしても表示されない |
| トークンのspan間に空白を挟まない（#1081） | Word候補がある単語を含む歌詞 | `.lyric`内の`</span>`と`<span>`の間に空白文字が入らない（「最高の行をコピー」でinnerTextをコピーした際に単語同士が連結され、余分なスペースが入らないようにするため） |

#### 7-14. `StatsView` (`/stats/`)（#334。グラフ表示設定のcookie保持、#1111）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| 曲が0件 | DBが空 | stat項目が1つも表示されない（song_count=0＝データなしとして全体を非表示） |
| 曲は存在し他の指標が0（回帰、コードレビュー指摘対応の仕様変更） | 曲が1件以上存在するがtotal_like等が0 | 「データなし」ではなく実際の値としてそのカードも表示される（`song_count`が0の時だけ全体を非表示にし、それ以外は個々の値が0でも表示する） |
| YouTube由来の指標のみYouTubeアイコン付き (#896) | view・likeを持つ曲が存在 | `stats_items`のうち`is_youtube`が付くのは「総再生回数」「総高評価数」のみで、レスポンスに`fa-youtube`が含まれる |
| songrangeによる絞り込み | `?songrange=subeana` | is_subeana=Trueの曲のみが集計される |
| 不正なsongrange | `?songrange=invalid` | "all"にフォールバックする |
| yearによる絞り込み | `?year=2024` | upload_time年が2024の曲のみが集計される |
| yearが"all"でもmonthのみで絞り込み | `?month=1` | 年をまたいで該当月の曲のみが集計される（#334で年月セレクトを独立表示に変更） |
| 月セレクトの常時表示 | yearを指定しない（"全ての年"） | 月セレクト(`#stats-month`)が非表示にならず常に表示される（#334で仕様変更） |
| songrangeラジオグループの表示 | is_subeana=True/Falseの曲がそれぞれ存在 | 全て/すべあな界隈曲のみ/以外の3択が表示される |
| songrangeラジオグループの非表示 | is_subeana=Trueの曲のみ存在 | ラジオグループ自体（3つとも）が表示されない（選んでも結果が変わらないため） |
| songrangeの自動解決 | is_subeana=Trueの曲のみ存在、songrange未指定 | ラジオグループが非表示になる代わりに`songrange`が自動的に"subeana"に解決され、絞り込み結果自体は正しい |
| 明示指定されたsongrangeも実在する方に強制（回帰、コードレビュー指摘対応） | is_subeana=Trueの曲のみ存在、`?songrange=xx`を明示指定 | ラジオグループが非表示のカテゴリを明示指定しても常に0件になる絞り込みは許さず、`songrange`は"subeana"に上書きされる |
| 数値でないyear（回帰、コードレビュー指摘対応） | `?year=abc` | 500エラーにならずHTTP 200、`year`は"all"にフォールバックする |
| 数値でないmonth（回帰、コードレビュー指摘対応） | `?month=abc` | 500エラーにならずHTTP 200、`month`は"all"にフォールバックする |
| 小数文字列のmonth（回帰、コードレビュー指摘対応） | `?month=1.5` | 500エラーにならずHTTP 200、`month`は"all"にフォールバックする |
| ゼロ埋め等のyearの正規化（回帰、コードレビュー指摘対応） | `?year=02024` | `context["year"]`が正規化された"2024"になり、年セレクトの選択状態も正しく一致する |
| グラフがsongrangeフィルターに連動（コードレビュー指摘対応の仕様変更） | `?songrange=subeana`、`Stats`にall/subeana/xxそれぞれのレコードが存在 | `context["monthly_stats"]`がsongrange="subeana"のレコードのみになる |
| グラフがyearフィルターに連動（コードレビュー指摘対応の仕様変更） | `?year=2024`、複数年の`Stats`レコードが存在 | `context["monthly_stats"]`が2024年の月のみになる |
| グラフがyear未指定のmonthのみフィルターにも連動（回帰、コードレビュー指摘対応） | `?month=1`（yearは指定しない）、複数年の`Stats`レコードが存在 | 統計カードと同様、`context["monthly_stats"]`も年をまたいだ該当月のみになる（以前はグラフ側だけmonth条件が無視されていた） |
| グラフの差分は絞り込み前の全期間から計算（回帰） | `?year=2025`指定、2024年12月と2025年1月の`Stats`が存在 | 表示範囲を2025年のみに絞り込んでも、`song_count_delta`は2024年12月との差分として正しく計算される |
| year選択肢は選択中のsongrangeに連動（回帰、コードレビュー指摘対応） | `?songrange=subeana`、xx曲のみの年とsubeana曲のみの年が混在 | `year_choices`にxx曲のみの年が含まれず、選択しても0件になる組み合わせを避けられる |
| メニューからの導線 | トップページのGET | `/stats/`へのリンクが記事とお問い合わせの間に含まれる |
| `highlighted_month`はyearのみ指定時はNone | `?year=2024`（monthは指定しない） | `context["highlighted_month"]`が`None` |
| `highlighted_month`はmonthのみ指定時もNone | `?month=1`（yearは指定しない） | `context["highlighted_month"]`が`None` |
| `highlighted_month`はyear・month両方指定時のみセット（コードレビュー指摘対応） | `?year=2024&month=6` | `context["highlighted_month"]`が`6`になり、JS側で棒グラフのその月だけ色を変えるための`highlighted-month-data`が埋め込まれる（グラフ側はmonthを無視してその年全体を表示するため、選択していた月をハイライトして元のフィルターとの対応を分かりやすくする） |
| グラフ表示設定はcookie未設定時デフォルト（#1111） | cookie無し | `context["chart_mode"]`が`"monthly"`、`context["chart_series"]`が`"song_count"`になり、対応するラジオボタンに`checked`が付く |
| グラフ表示設定はcookieの値を反映（#1111） | `stats_chart_mode=cumulative`・`stats_chart_series=total_view`のcookieを送信 | `context["chart_mode"]`が`"cumulative"`、`context["chart_series"]`が`"total_view"`になり、対応するラジオボタンのみに`checked`が付く |
| グラフ表示設定はsongrange変更（ページ全体の再読み込み）を挟んでも維持される（#1111の再現ケース） | `stats_chart_mode=cumulative`のcookieを送信した状態で`?songrange=subeana`にアクセス | `context["chart_mode"]`が`"cumulative"`のまま（`chart-mode`/`chart-series`は`songrange`/`year`/`month`用のformの外側にあり、これらの変更时のページ全体再読み込みでは送信されないため、cookie側で維持する） |
| 不正なグラフ表示設定cookieはデフォルトにフォールバック（#1111） | `stats_chart_mode`/`stats_chart_series`に許可されていない値を送信 | `context["chart_mode"]`が`"monthly"`、`context["chart_series"]`が`"song_count"`にフォールバックする |

#### 7-15. `AuthorStatsView` (`/authors/<id>/stats/`)（#334）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する作者ID | 有効なauthor_id | HTTP 200 |
| 存在しない作者ID | 無効なauthor_id | HTTP 404 |
| 数値でないyear（回帰、コードレビュー指摘対応） | `?year=abc` | 500エラーにならずHTTP 200、`year`は"all"にフォールバックする |
| 数値でないmonth（回帰、コードレビュー指摘対応） | `?month=abc` | 500エラーにならずHTTP 200、`month`は"all"にフォールバックする |
| 対象authorの曲のみ集計 | 他authorの曲も存在 | 対象author以外の曲は集計対象に含まれない |
| 合作人数(重複あり)・合作人数(重複なし)は本人を除く | 対象authorと共作者1名の曲が存在 | 「合作人数(重複あり)」「合作人数(重複なし)」がともに1になる（本人はカウントしない）。総合統計ページの「総作者数」は表示されない |
| YouTube由来の指標のみYouTubeアイコン付き (#896) | view・likeを持つ曲が存在 | `stats_items`のうち`is_youtube`が付くのは「総再生回数」「総高評価数」のみで、レスポンスに`fa-youtube`が含まれる |
| songrangeラジオグループは対象author自身の曲を基準に判定 | サイト全体にはxx曲が存在するが、対象author自身はsubeana曲しか持たない | サイト全体の状況に関わらず、対象author基準でラジオグループ自体が非表示になり`songrange`が"subeana"に解決される |
| year選択肢は対象author自身の投稿年のみ（回帰、コードレビュー指摘対応） | サイト全体には別年の曲があるが、対象author自身はある年にしか投稿していない | `year_choices`に対象author自身が投稿していない年が含まれない |
| month選択肢は対象author自身が実際に投稿した月のみ（回帰、コードレビュー指摘対応） | 対象authorがある年の6月にのみ投稿している | その年を選択した際の`month_choices`が`[6]`のみになる（投稿していない月は選択肢に出ない） |
| year選択肢は投稿の無い間の年を除く（回帰、コードレビュー指摘対応） | 対象authorが2020年・2024年にのみ投稿（2021〜2023年は無し） | `year_choices`が`[2020, 2024]`になる（連続レンジにはならない） |
| 年変更でその年に存在しない月を選んでいた場合はmonthが自動的に"all"に戻る（回帰） | `?year=2025&month=6`（2025年に6月の投稿が無い） | `month`が`"all"`にフォールバックする（`year`自体は`"2025"`のまま） |

#### 7-16. action-buttonの要素（#450）

`<a><div class="dummybutton">`のようにdivで作っていたdummybuttonを`action-button`（並べる枠は`action-buttons`）に改名し、画面遷移はhref付きの`<a class="action-button">`、JSで処理するボタンは`<button type="button" class="action-button">`で実装する（`<a>`の中に`<button>`を入れるのはHTMLの仕様違反のため、遷移は`<a>`のままにする）。`<button>`の中に`<p>`は入れられないため、ボタンの文言は`<a>`も含めて`<span>`に統一する。見た目（`button`のmargin・font-size・line-height・box-sizingの既定値の打ち消し）とキーボード操作時のフォーカス表示（`:focus-visible`）はDjangoテストでは確認できないため、Playwrightで確認する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| divのaction-buttonが無い | トップ・曲・曲の編集履歴・曲の編集（`?toast`付き）・編集履歴一覧・編集者・作者・別名一覧・別名編集・別名削除・名義の統一の確認・歌詞の作成結果の各ページ | `<a href>`または`<button>`のaction-buttonが1つ以上あり、`<div class="action-button">`と旧クラス名の`dummybutton`は含まれない |
| ボタンの文言はspan | 上記の各ページ | 全てのaction-buttonの文言が`<span>`で、`<p>`は含まれない |
| 画面遷移のボタンはhref付きのa | 曲のページ | 「編集/削除申請」「編集履歴」が`<a href="..." class="action-button">`になる |
| 画面遷移のボタン（黒）はhref付きのa | 別名削除ページ | 「キャンセル」が`<a href="/authors/<id>/aliases/" class="action-button black-action-button">`になる |
| 編集履歴の操作ボタンはbutton | 編集履歴一覧・編集者・曲の編集履歴の各ページ | 「再読み込み」「全て開く/閉じる」が`<button type="button" id="history-reload" class="action-button">`・`<button type="button" id="history-open-all" class="action-button">`になる |
| 別名一覧の再読み込みボタンはbutton | 別名一覧ページ | `<button type="button" id="alias-reload" class="action-button black-action-button">`になる |
| 歌詞の作成結果のボタンはbutton | 歌詞の作成結果ページ | 「最高の行をコピー」「再作成」が`<button type="button" id="copy" class="action-button">`・`<button type="button" id="regenerate" class="action-button">`になる |
| メンテナンス画面の再読み込みボタンはbutton | `IS_MAINTENANCE=True`（`_load_maintenance`をモック）で`/ai/result/`にアクセス | `maintenance.html`が使われ、`<button type="button" id="maintenance-reload" class="action-button">`（文言は`<span>再読み込み</span>`）になる |

#### 7-17. `SettingView` (`/setting/`)（#1164）

検索画面のセクションの「フォームボタン」（`form_button`）で、検索画面のフォームを切り替えるラジオボタン（`#search-form-radios`）を「アイコンのみ」（`icon`）か「アイコンと文字」（`icon_text`、デフォルト）にできる。「アイコンのみ」の場合は`#search-form-radios`に`icon-only`クラスを付け、`songs.css`でラベルの`::before`（丸）と`.icon-p-big`（文字）を非表示にする。文字は読み上げでラジオボタンの名前として使われるよう、`display: none`ではなく見えない状態にする。並び替え等のフォーム内のラジオボタンや、検索画面以外のラジオボタンには影響しない。見た目はDjangoテストでは確認できないため、Playwrightで確認する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| フォームボタンの設定のデフォルト | cookie無し | 「フォームボタン」の`<select id="form_button">`が表示され、選択肢は「アイコンのみ」（`icon`）・「アイコンと文字」（`icon_text`）の順で、「アイコンと文字」が選択される |
| フォームボタンの設定のcookieを反映 | `form_button=icon`のcookieを送信 | 「アイコンのみ」が選択される |
| チュートリアルのアイコン | GETリクエスト | 選択肢の保存のチュートリアル（`data-tutorial="select"`）のアイコンは「検索の選択肢の保存」にのみ付き、「フォームボタン」には付かない |

#### 7-18. `SaveSettingsView` (`/api/setting/save/`)（#1164）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| フォームボタンの設定の保存 | `{"cookies": {"form_button": "icon"}}`・`{"cookies": {"form_button": "icon_text"}}` | HTTP 200、`form_button`のcookieが送信した値で保存される |
| 許可されていない値は保存しない | `{"cookies": {"form_button": "text"}}`・`{"cookies": {"form_button": "<script>"}}` | HTTP 200、`form_button`のcookieは保存されない |

#### 7-19. `robots` (`/robots.txt`)（#1172）

`subekashi/static/subekashi/robots.txt`の内容を、`/static/`へリダイレクトせず`/robots.txt`で直接返す。robots.txtの`Disallow`は完全なURLではなくパス（`/`から始まる値）で書かないとどのURLにもマッチしない。Disallowが巡回を制限するかの判定は、`*`を任意の文字列とみなした前方一致で行う。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| robots.txtを直接返す | GETリクエスト | HTTP 200、`Content-Type`が`text/plain; charset=utf-8`で、`User-agent: *`とSitemapの行が含まれる |
| Disallowの値はパス | GETリクエスト | `Disallow`の行が1つ以上あり、全ての値が`/`から始まる |
| Disallowが対象のページにマッチする | 曲の編集・曲の削除・編集者・設定の各ページのパス | いずれかの`Disallow`にマッチする |
| Disallowが対象外のページにマッチしない | トップ・曲の検索・曲・曲の編集履歴の各ページのパス | どの`Disallow`にもマッチしない |

#### 7-20. OGPのメタタグ（#1058）

全ページが継承する`base/base.html`のOGPのメタタグを確認する。OGPの画像はページごとに`/ogp/<token>.png`（`ogp_image`ビュー）で生成し、`token`は`metatitle`を署名したもの（`lib/ogp.py`の`make_ogp_token`）。SNS側で読み込めるよう、URLはcontext processorの`root_url`（`django.conf.settings.ROOT_URL`）を付けた絶対URLにする。OGPのタグは`{% block ogp %}`にまとめ、404・500ページでは出さない。SNSで実際にカードが表示されるかはDjangoテストでは確認できないため、デプロイ後にX・Discordで確認する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| og:*はproperty属性 | トップページ | `<meta property="og:type" content="website">`が含まれ、`name="og:`は含まれない |
| 画像はページごとのOGP画像のURL | トップページ | `og:image`が`{ROOT_URL}/ogp/<token>.png?v={OGP_VERSION}`で、`token`を`load_ogp_token`で復元すると`トップ`になる |
| twitter:imageはog:imageと同じ | トップページ | `twitter:image`が`og:image`と同じURLになる |
| 画像のタイトルは各ページのmetatitle | 曲・統計・編集者の各ページ | `token`を復元すると、それぞれ`{曲名} / {作者名}`・`統計`・`全て{id}の所為です。`（EditorViewは`metatitle`に`Editor`のインスタンスを渡す）になる |
| og:imageのURLで画像が返る | 曲のページの`og:image`のパスにGET | ステータス200で、`Content-Type`が`image/png`になる |
| 404ページにはOGPのタグを出さない | 存在しない曲（`/songs/999999999/`、`SongView`が404.htmlを表示）・存在しないURL（`/no-such-page/`、handler404が404.htmlを表示） | ステータス404で、`property="og:`・`name="twitter:`は含まれず、`<meta name="description">`は含まれる |
| 500ページにはOGPのタグを出さない | `subekashi/500.html`を`render_to_string`で描画 | `property="og:`・`name="twitter:`は含まれない |
| `ROOT_URL`の設定を使う | `override_settings(ROOT_URL="https://example.com")`でトップページ | `og:url`が`https://example.com/`になる（context processorが`config.settings`ではなく`django.conf.settings`から読むため） |
| 共通の画像のファイルがある | — | `finders.find("subekashi/image/ogp.png")`が`None`でない |
| 画像のサイズと代替テキスト | トップページ | `og:image:width`が`1200`、`og:image:height`が`630`、`og:image:alt`が`トップ \| 全て歌詞の所為です。`になる |
| twitter:card | トップページ | `<meta name="twitter:card" content="summary_large_image">`が含まれる |
| サイト名とロケール | トップページ | `og:site_name`が`全て歌詞の所為です。`、`og:locale`が`ja_JP`になる |
| og:urlはページごとのURL | トップ・曲一覧・曲の各ページ | `og:url`が`{ROOT_URL}{ページのパス}`になる |
| og:urlにクエリ文字列を含めない | `/songs/?keyword=OGP` | `og:url`が`{ROOT_URL}/songs/`になる |
| og:titleとog:description | トップページ | `og:title`が`トップ \| 全て歌詞の所為です。`、`og:description`が`DEFAULT_DESCRIPTION`になる |

#### 7-21. `ogp_image` (`/ogp/<token>.png`)（#1058）

ページごとのOGP画像を返す。画像はリクエストごとにメモリ上で生成してDjangoのキャッシュ（設定が無いため既定のメモリ内キャッシュ）に1日保存し、ファイルには保存しない。各テストの前に`cache.clear()`する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| PNGを返す | `make_ogp_token("トップ")`のトークン | ステータス200、`Content-Type`が`image/png`で、画像のサイズが1200×630 |
| 長期間キャッシュさせる | 同上 | `Cache-Control`が`public, max-age={LONG_TERM_COOKIE_AGE}`（タイトルが変わるとURLも変わるため） |
| バージョンのクエリを受け付ける | `?v={OGP_VERSION}`付き | ステータス200（ビューではクエリを使わない） |
| 生成した画像をキャッシュする | 同じURLに2回GET（`render_ogp_image`を`wraps`でモック） | 描画は1回だけで、2回とも同じ画像 |
| 条件付きリクエスト | 1回目の`ETag`を`If-None-Match`に付けてGET | ステータス304で、`ETag`と`Cache-Control`（1年）が付き、描画しない |
| ETagはタイトルごとに異なる | `トップ`と`統計` | 異なる`ETag` |
| フォントを読み込めない | `get_font`が`OSError`を送出（モック） | ステータス200で共通の画像（`ogp.png`）の中身を返し、`Cache-Control`は`public, max-age={SHORT_TERM_COOKIE_AGE}`、`ETag`は付けない。共通の画像はキャッシュしないため、次のリクエストでは生成した画像を返す（リダイレクトをたどらないクローラーがあるため、リダイレクトにはしない） |
| タイトルが空 | `signing.dumps("", salt=OGP_SALT, compress=True)`のトークン | ステータス404 |
| 不正なトークン | `/ogp/invalid-token.png` | ステータス404 |
| saltが異なるトークン | `signing.dumps("トップ", compress=True)`（saltなし）のトークン | ステータス404（署名の鍵が同じでも他の用途のトークンは受け付けない） |

##### レート制限

新しく描画するときだけ、`X-Real-IP`ごとに毎秒5回までに制限する（キャッシュ済みの画像は数えない）。PythonAnywhereでは`REMOTE_ADDR`がロードバランサーのIPになるため、ロードバランサーが付ける`X-Real-IP`を使う（`key="ip"`で、`settings.RATELIMIT_IP_META_KEY`の`get_client_ip`から取る。#1188）。制限には`django_ratelimit`の`is_ratelimited`を使い、制限を超えたら429を返す（キャッシュ済みの画像は数えないため、デコレーターではなくビューの中で判定する）。1秒の区切りをまたいでカウントがリセットされないよう、`django_ratelimit.core.time`をモックして時刻を固定する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 1秒に6枚目の描画で制限 | 同じ`X-Real-IP`で異なる6つのタイトルにGET | 5回目まではステータス200、6回目は429で、`Retry-After`が`1`、`Cache-Control`が`no-store`（SNSのクローラーに失敗をキャッシュさせない） |
| キャッシュ済みの画像は制限しない | 制限に達した後、描画済みのタイトルにGET | ステータス200 |
| X-Real-IPごとに制限 | IP Aで5枚描画した後、IP B・IP Aで新しいタイトルにGET | IP Bは200、IP Aは429 |
| HEADも回数に数える | 同じ`X-Real-IP`で異なる5つのタイトルにHEADした後、新しいタイトルにGET | 429 |

---

### 8. REST API ビュー

**テストファイル案**: `tests/test_api.py`

#### 8-1. `SongAPI` (`/api/song/`)

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| パラメータなし | GETリクエスト | HTTP 200、JSON形式の曲一覧 |
| キーワード検索 | `?keyword=テスト` | HTTP 200、絞り込み結果 |
| guesserのURL検索（#1117） | `?guesser=https://www.youtube.com/watch?v=<id>` | `https://youtu.be/<id>`のリンクを持つ曲のみが返る |
| ページネーション | `?page=1&size=5` | HTTP 200、最大5件 |
| 不正なsize | `?size=-1` | HTTP 200、デフォルトサイズで処理 |
| 統計情報の含有 | GETリクエスト | レスポンスに `count`, `page`, `max_page` が含まれる |
| `is_lack=False`（#970） | URLあり・歌詞ありの曲とURLなしの曲が存在、`?is_lack=False` | 未完成の曲（URLなし）が除外される |
| `is_special=True`（#939） | スペシャルデザインの曲と通常の曲が存在、`?is_special=True` | スペシャルデザインの曲のみ返される |
| `is_collab=True`（#943） | 作者2人の曲と作者1人の曲が存在、`?is_collab=True` | 合作の曲のみ返される |
| `sort=-imitated_count`（#542） | 曲1が曲2を模倣、`?sort=-imitated_count` | 模倣曲の数が多い曲2、曲1の順で返される |

#### 8-2. `EditorIsOpenView` (`/api/editor/is_open`)

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200、`is_open` フィールドを含むJSON |

#### 8-3. `WordCandidatesView` (`/api/word/candidates/`)（#1053）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| word・hinshi未指定 | パラメータなし | HTTP 400 |
| 候補が存在する場合 | `?word=走る&hinshi=動詞&katsuyou=基本形` | HTTP 200、該当する候補一覧 |
| 候補が存在しない場合 | 未登録の単語 | HTTP 200、空配列 |
| 活用形が異なる場合 | hinshiは一致するがkatsuyouが異なる候補のみ存在 | HTTP 200、空配列 |
| 候補が10件超える場合 | 候補15件登録済み | 最大10件に絞られる |

#### 8-4. `AiWordSwapView` (`/api/ai/swap/`)（#1053）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な入れ替え | 実在するbase_id・token_index・候補 | HTTP 201、新規`Ai`レコード（`score=0`, `genetype="janome"`）が作成される |
| 元レコードへの影響 | 正常な入れ替え後 | 元の`Ai`レコードの`lyrics`は変更されない |
| 存在しないbase_id | 未登録のID | HTTP 404 |
| レガシーgenetype="model"のbaseは対象外 | `genetype="model"`のAiレコードをbase_idに指定 | HTTP 404（単語入れ替えはgenetype="janome"のAiレコードからのみ許可） |
| 範囲外のtoken_index | 歌詞のトークン数を超える値 | HTTP 400 |
| 置き換え対象外の品詞 | 助詞など`REPLACEABLE_HINSHIS`外のトークン | HTTP 400 |
| Wordに存在しない候補 | 実在しない候補語 | HTTP 400、`Ai`レコードは作成されない |
| 活用形が異なる候補 | hinshiは一致するがkatsuyouが異なる候補 | HTTP 400（文法破綻を防ぐため。katsuyouはクライアント入力を信用せず、base_idの歌詞をサーバー側で再トークナイズして取得） |
| 同じ入れ替え結果の重複防止 | 同一の`base_id`・`token_index`・`candidate`で2回POST | 2回目は新規`Ai`レコードを作成せず、既存レコードのidを返す |
| 重複判定はgenetypeも考慮 | `lyrics`は同じだが`genetype="model"`の既存`Ai`が存在 | 既存レコードを誤って再利用せず、`genetype="janome"`の新規レコードを作成する |
| レスポンスステータスの正確性 | 同一の`base_id`・`token_index`・`candidate`で2回POST | 1回目はHTTP 201（新規作成）、2回目はHTTP 200（既存レコードの再利用） |
| レスポンスに再トークナイズ済みのtokensを含める | 正常な入れ替え後 | 入れ替え後の歌詞を実際に再トークナイズした`surface`・`hinshi`・`katsuyou`・`index`・`is_replaceable`を含む。janomeは文脈依存のトークナイザのため、クライアント側が古い`token_index`を使い回すと同じ行での連続入れ替え時にズレる可能性があり、それを防ぐためクライアント側でその行のDOMを丸ごと作り直せるようにする |

#### 8-5. `SongEditInitView` (`/api/song_edit_init/`)（#1135）

`song_edit.js`は模倣一覧の表示と送信する模倣曲IDのどちらも`imitate_songs`を元にするため、模倣元が1件でも欠けると保存時にその模倣情報が消える。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 模倣元がない曲 | `?song_id=<id>&fetch_imitate=1` | `imitate_songs`が`None`ではなく空配列 |
| 模倣元が検索のデフォルト件数（50件）超 | 模倣元51件の曲 | 51件すべてが返る |
| 削除済み・下書きの模倣元 | `is_deleted=True`・`is_draft=True`の曲を模倣元に持つ曲 | 除外されずにすべて返る |
| 存在しないsong_id | `?song_id=99999&fetch_imitate=1` | HTTP 200（500にならない）、`imitate_songs`が`None`（`song_edit.js`は読み込み失敗として登録ボタンを無効化する） |
| 数値でないsong_id | `?song_id=abc&fetch_imitate=1` | HTTP 200（500にならない）、`imitate_songs`が`None` |
| 上付き数字のsong_id | `?song_id=²&fetch_imitate=1` | HTTP 200（500にならない）、`imitate_songs`が`None`（`str.isdigit()`はTrueだが`int()`で変換できない） |
| 範囲外のsong_id | 30桁の数字 | HTTP 200（500にならない）、`imitate_songs`が`None` |

#### 8-6. スロットリングのIP（`lib/throttling.py`）（#1192）

**テストクラス**: `ApiThrottleClientIPTest`・`ApiThrottleIdentTest`（`tests/test_api.py`）

DRFの既定の`get_ident`は`X-Forwarded-For`の全体を識別子にするため、クライアントが値を変えるだけで制限を回避できる。`subekashi.lib.throttling`の`AnonRateThrottle`・`UserRateThrottle`は`get_ident`を`lib/ip.py`の`get_client_ip`で上書きし、`X-Real-IP`（無ければ`REMOTE_ADDR`）で数える。`ApiThrottleClientIPTest`は`SongAPI`（毎秒2回まで）で確認し、1秒の区切りをまたいでカウントがリセットされないよう、`rest_framework.throttling.SimpleRateThrottle.timer`をモックして時刻を固定する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 1秒に3回目で制限 | 同じ`X-Real-IP`で`/api/song/`に3回GET | 2回目まではHTTP 200、3回目は429 |
| X-Real-IPごとに制限 | IP Aで2回GETした後、IP B・IP AでGET | IP Bは200、IP Aは429 |
| X-Forwarded-Forでは回避できない | 同じ`X-Real-IP`で`X-Forwarded-For`を毎回変えて3回GET | 3回目は429（#1189の不一致の記録は`assertLogs`で受け取る） |
| X-Real-IPが無ければREMOTE_ADDRごとに制限 | `REMOTE_ADDR` Aで2回GETした後、`REMOTE_ADDR` B・AでGET | Bは200、Aは429 |
| 全てのAPIのビューのスロットリング | `subekashi.urls`から集めたDRFのビュー（`APIRootView`・既定の`AnonRateThrottle`を使うビューを含む）の全ての`throttle_classes`で、`REMOTE_ADDR: 10.0.0.1`・`X-Real-IP: 203.0.113.1`・`X-Forwarded-For: 198.51.100.1`のリクエストの`get_ident` | 全て`203.0.113.1`（ビューを追加したときにDRFのクラスをそのまま使っていないかを確認する） |

---

### 9. ミドルウェア

**テストファイル案**: `tests/test_middleware.py`

#### 9-1. `RatelimitMiddleware`

`@ratelimit(block=True)`が送出する`Ratelimited`は`PermissionDenied`のサブクラスで、ミドルウェアの`__call__`に届く前に403のレスポンスになるため、`process_exception`で429にする（#1187）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 通常リクエスト | Ratelimited例外なし | 通常のレスポンスを返す |
| レート制限を超えた場合 | `process_exception`に`Ratelimited`を渡す | HTTP 429、`{"error": "Rate limit exceeded"}`、`Retry-After`が`1`、`Cache-Control`が`no-store`（`CacheControlMiddleware`にpublicのキャッシュを付けさせない） |
| Ratelimited以外のPermissionDenied | `process_exception`に`PermissionDenied`を渡す | `None`（Djangoの通常の処理で403になる） |

ミドルウェアに例外を直接渡すテストでは403になる不具合を検出できないため、Clientで実際にリクエストするテストを結合テスト計画書の「16. レート制限フロー」に記載している。

#### 9-2. `CacheControlMiddleware`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 静的ファイルURL | `/static/` へのリクエスト | Cache-Controlヘッダーが設定される |
| 通常ページURL | `/` へのリクエスト | Cache-Controlが適切に設定される |

#### 9-3. `ContentSecurityPolicyMiddleware`（#1126）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| HTMLレスポンス | `HttpResponse` | `Content-Security-Policy`の`script-src`に`request.csp_nonce`のnonceが含まれる |
| nonceの一意性 | 2回リクエスト | リクエストごとに異なるnonceが生成される |
| HTML以外のレスポンス | `JsonResponse` | `Content-Security-Policy`ヘッダーが付与されない |
| 既存のCSPヘッダー | レスポンスに設定済み | 上書きされない |
| DEBUG時のサーバーエラー | `DEBUG=True`、HTTP 500 | Djangoのエラーページがインラインスクリプトを使うため付与されない |
| 本番のサーバーエラー | `DEBUG=False`、HTTP 500 | 付与される |
| インラインスクリプトの禁止 | `script-src` | `'unsafe-inline'`・`'unsafe-eval'`・`*`を含まない |
| 制限的なディレクティブ | - | `default-src 'self'`・`object-src 'none'`・`base-uri 'self'`・`form-action 'self'`・`frame-ancestors 'none'` |

#### 9-4. `RestrictIPMiddleware` — `X-Forwarded-For` の先頭と `X-Real-IP` の不一致の記録（#1189）

`get_ip` を `X-Real-IP` に切り替える前に、編集者が変わるリクエストの件数を本番で確認するための一時的な記録。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 先頭が一致しない | `X-Forwarded-For: 198.51.100.1, 203.0.113.1`、`X-Real-IP: 203.0.113.1`、`POST /songs/1/edit` | `subekashi.lib.ip` に WARNING が1件記録され、メソッド・パス（`repr` の形式）・`X-Forwarded-For` の IP の数（2）を含み、IP を含まない。レスポンスはそのまま返す |
| パスに改行を含む（ログインジェクション） | パスが `/songs/%0d%0a...`、先頭が一致しない | 記録されたメッセージに改行（`\r`・`\n`）を含まず、`\r\n` とエスケープされている |
| 一致する | `X-Forwarded-For` と `X-Real-IP` が同じ IP | 記録されない |
| 先頭が一致し、後ろにプロキシの IP が続く | `X-Forwarded-For: 203.0.113.1, 10.0.0.1`、`X-Real-IP: 203.0.113.1` | 記録されない（先頭だけを比べる） |
| `X-Real-IP` が無い | `X-Forwarded-For` のみ | 記録されない |
| `X-Forwarded-For` が無い | `X-Real-IP` のみ | 記録されない |

#### 9-5. `RestrictIPMiddleware` — 確認用のパスへのリクエストの IP の記録（#1191）

本番で `REMOTE_ADDR` がロードバランサーの IP になり、`X-Real-IP` がロードバランサーに付け直されているかを確認するための一時的な記録。`/x-real-ip-check` で始まるパスへのリクエストだけ、`subekashi.lib.ip` に WARNING を1件記録する。IP は記録せず、`REMOTE_ADDR`・`X-Real-IP` の種類（なし・IPでない・グローバル・グローバルでない）と、ヘッダー同士が一致するかだけを記録する。テストでグローバルな IP が必要な箇所は `8.8.8.8` を使う（ドキュメント用の `198.51.100.0/24`・`203.0.113.0/24` はグローバルでない）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| ロードバランサーが付け直した | `POST /x-real-ip-check-1`、`REMOTE_ADDR: 10.0.0.1`、`X-Forwarded-For: 198.51.100.1, 8.8.8.8`、`X-Real-IP: 8.8.8.8` | `REMOTE_ADDR: グローバルでない`、`X-Real-IP: グローバル`、`REMOTE_ADDR` と `X-Real-IP` が一致: False、IP の数: 2、先頭が一致: False、末尾が一致: True。IP を含まない。レスポンスはそのまま返す |
| クライアントが送った `X-Real-IP` がそのまま届いた | `POST /x-real-ip-check-2`、`REMOTE_ADDR: 10.0.0.1`、`X-Forwarded-For`・`X-Real-IP` が `198.51.100.1` | 1件だけ記録され、`X-Real-IP: グローバルでない`、IP の数: 1、先頭・末尾が一致: True。IP を含まない |
| `REMOTE_ADDR` がクライアントの IP | `POST /x-real-ip-check-3`、`REMOTE_ADDR`・`X-Real-IP` が `8.8.8.8`、`X-Forwarded-For` なし | `REMOTE_ADDR: グローバル`、`REMOTE_ADDR` と `X-Real-IP` が一致: True、IP の数: 0、先頭・末尾が一致: False。IP を含まない |
| `X-Real-IP` が無い・IP でない | `X-Real-IP` なし、`X-Real-IP: not-an-ip` | それぞれ `X-Real-IP: なし`・`X-Real-IP: IPでない`、`REMOTE_ADDR` と `X-Real-IP` が一致: False |
| パスに改行を含む（ログインジェクション） | パスが `/x-real-ip-check-%0d%0a...` | 記録されたメッセージに改行（`\r`・`\n`）を含まず、`\r\n` とエスケープされている |
| 確認用のパス以外 | `POST /songs/1/edit`、`X-Forwarded-For`・`X-Real-IP` が同じ IP | 記録されない |

---

### 10. `lib/song_search.py` — 検索機能

**テストファイル案**: `tests/test_lib_song_search.py`

#### 10-1. `song_search(querys)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 空のクエリ | `{}` | 全曲を返す、statisticsに`count`, `page`, `max_page`が含まれる |
| page=1, size=10 | `{"page": "1", "size": "10"}` | 最大10件の曲 |
| 不正なpage | `{"page": "abc"}` | デフォルト`page=1`で処理 |
| 不正なsize | `{"size": "0"}` | デフォルトsize(50)で処理 |
| `size` による `max_page` の計算 | 曲100件, `size=10` | `max_page=10` |
| バリデーションエラーのあるパラメータ | 不正なfiltersetパラメータ | `ValidationError` が発生 |

#### 10-2. sort とフィルターの組み合わせ（distinct適用後もソート順が維持されること）

`keyword` や `author` 等のフィルターを使うと `distinct()` のため queryset が再構築される。
その際にソート順が失われないことを確認する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| keyword + sort=title | `{"keyword": "...", "sort": "title"}` | タイトル昇順で返される |
| keyword + sort=-title | `{"keyword": "...", "sort": "-title"}` | タイトル降順で返される |
| keyword + sort=id | `{"keyword": "...", "sort": "id"}` | ID昇順で返される |
| keyword + sort=-id | `{"keyword": "...", "sort": "-id"}` | ID降順で返される |
| title + sort=title | `{"title": "...", "sort": "title"}` | タイトル昇順で返される |
| title + sort=-title | `{"title": "...", "sort": "-title"}` | タイトル降順で返される |

#### 10-3. author/author_exact/keywordフィルターの別名（双方向）対応

`author(yamada)` に別名 `sasaki`（`Author(sasaki)` も別途存在）を登録したシナリオで、
`song_search()` 経由でも双方向解決が機能することを確認する。owner名(`yamada`)とtarget名
(`sasaki`)は互いの部分文字列にならない組み合わせを使い、素の作者名一致だけで
逆方向テストが偶然パスしないようにしている。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| author（正方向） | `{"author": "sasaki"}` | `yamada`・`sasaki`双方の曲がヒット |
| author（逆方向） | `{"author": "yamada"}` | `yamada`・`sasaki`双方の曲がヒット |
| author_exact（逆方向） | `{"author_exact": "yamada"}` | `yamada`・`sasaki`双方の曲がヒット |
| keyword（逆方向） | `{"keyword": "yamada"}` | `yamada`・`sasaki`双方の曲がヒット |

#### 10-4. is_lackフィルター（True・False・フィルタなしの3値）

`is_lack=False` は `filter_by_lack()` を `exclude()` で否定するため、多値リレーション（`imitates`）や `Exists` を含む各条件で正しく否定されることを検証する。
完成した曲（URLを2つ持つ曲・模倣元を持つ曲・歌詞なしのインスト曲・URLなしの非公開/削除済みの曲）と、未完成の曲（URLなしで非公開/削除済みでない曲・模倣元が無いすべあな界隈曲・歌詞が空でインスト曲でない曲）が存在するシナリオで検証する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| is_lack=True | `{"is_lack": "True"}` | 未完成の曲のみ重複なく返される |
| is_lack=False | `{"is_lack": "False"}` | 未完成の曲が除外され、完成した曲が重複なく返される |
| is_lack指定なし | `{}` | 全ての曲が返される |
| True と False の関係 | `{"is_lack": "True"}` と `{"is_lack": "False"}` | 結果が互いに素で、合わせると全件になる |

#### 10-5. 空白のみの検索語（#1125）

テキスト系フィルター（`title`・`author`・`lyrics`・`url`・`title_exact`・`author_exact`・`keyword`・`guesser`）は
前後の空白を除去するが、空白のみの入力は空文字にせず検索語として扱う。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| keywordが全角スペースのみ | `{"keyword": "　"}` | タイトル・歌詞に全角スペースを含む曲のみヒット |
| keywordが半角スペースのみ | `{"keyword": " "}` | 半角スペースを含む曲のみヒット |
| titleが全角スペースのみ | `{"title": "　"}` | 全角スペースを含むタイトルの曲がヒットし、空白なしの曲はヒットしない |
| lyricsが全角スペースのみ | `{"lyrics": "　"}` | 歌詞に全角スペースを含む曲のみヒット |
| 前後に空白のあるkeyword | `{"keyword": "　空白なし "}` | 前後の空白が除去され`空白なし`で検索される |
| keywordが空文字 | `{"keyword": ""}` | フィルタは適用されず全曲を返す |

#### 10-6. is_specialフィルター（True・False・フィルタなしの3値、#939）

スペシャルデザインの曲（`is_special=True`）と通常の曲が存在するシナリオで検証する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| is_special=True | `{"is_special": "True"}` / `"true"` | スペシャルデザインの曲のみ返される |
| is_special=False | `{"is_special": "False"}` / `"false"` | スペシャルデザインの曲が除外される |
| is_special指定なし | `{}` | 全ての曲が返される |

#### 10-7. is_collabフィルター（True・False・フィルタなしの3値、#943）

作者2人の合作の曲と作者1人の曲が存在するシナリオで検証する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| is_collab=True | `{"is_collab": "True"}` / `"true"` | 合作の曲のみ返される |
| is_collab=False | `{"is_collab": "False"}` / `"false"` | 合作の曲が除外される |
| is_collab指定なし | `{}` | 全ての曲が返される |
| authorフィルタとの組み合わせ | `{"is_collab": "True", "author": "合作検索作者"}` | 2人の作者の両方にヒットしても合作の曲が重複せず1件だけ返される |

#### 10-8. 模倣元の数・模倣曲の数のソート（#542）

曲Aが曲B・Cを、曲Dが曲Bを模倣しているシナリオで検証する（模倣元の数: A=2, D=1, B=C=0 / 模倣曲の数: B=2, C=1, A=D=0）。
`imitates` をJOINすると曲が重複するため、中間テーブルで曲ごとに数えたサブクエリで並び替え、数が同じ曲は登録日の遅い順（`-id`）で並べる。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 模倣元の数が多い順 | `{"sort": "-imitate_count"}` | A, D, C, B の順 |
| 模倣元の数が少ない順 | `{"sort": "imitate_count"}` | C, B, D, A の順 |
| 模倣曲の数が多い順 | `{"sort": "-imitated_count"}` | B, C, D, A の順 |
| 模倣曲の数が少ない順 | `{"sort": "imitated_count"}` | D, A, C, B の順 |
| distinctが適用されるフィルタとの組み合わせ | `keyword` / `imitate` / `imitated` と組み合わせる | 重複せず、ソート順が維持される |
| 件数の取得では並び替えない（#1124） | `{"keyword": "...", "sort": "-imitated_count", "count": True}` | 件数取得（`COUNT(*)`）のSQLに模倣曲の数のサブクエリと `ORDER BY` が含まれない |

---

### 11. モデル — 基本動作

**テストファイル案**: `tests/test_models.py`

#### 11-1. `Song` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| 曲の作成 | `Song.objects.create(title="テスト曲", ...)` | DBに保存される |
| `authors_str()` メソッド | 複数作者を持つ曲 | 作者名がカンマ区切りで返される |
| `is_questionable` のデフォルト値 | フラグ未指定で作成 | `is_questionable == False` |
| `is_deleted=True` の曲 | 削除フラグを立てる | DBに残るが削除済みとして扱われる |
| ManyToMany: authors | `song.authors.add(author)` | 作者が曲に紐付く |
| ManyToMany: imitates (自己参照) | `song.imitates.add(other_song)` | 模倣関係が成立する |

#### 11-2. `Author` モデル

`icontains`/`iexact`はDB照合順序に依存しないよう`subekashi/lib/db_lookups.py`でUPPER()を使った
独自実装に差し替えている（#1092）。`exact`/`contains`/`=`は元々のDB照合順序（MySQL/SQLite
いずれもバイト完全一致）に依存したままで、大文字小文字を区別する。CI（`.github/workflows/test.yml`）
はSQLiteのみで実行されるため、MySQL固有の照合順序に関する回帰は本セクションのテストケースを
ローカルのMySQL環境（`USE_MYSQL=True`）で手動実行して確認する必要がある。

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| 作者の作成 | `Author.objects.create(name="テスト作者")` | DBに保存される |
| `name` のユニーク制約 | 同じ名前で2件作成 | `IntegrityError` が発生 |
| Strict Modeによるmax_length超過の拒否 (#1091、MySQLのみ) | `max_length=255`を超える`name`で`save()` | `DataError`が発生（`config/settings.py`のinit_commandでSTRICT_TRANS_TABLESを有効化しているため） |
| `name` の大文字小文字違いは別レコード (#1092) | `"MoAI"`と`"moai"`をそれぞれ作成 | 両方ともDBに保存される（一意制約はバイト完全一致で判定） |
| `name=`によるexact matchは大文字小文字を区別する (#1092) | 上記の状態で`filter(name="MoAI")` | `"MoAI"`のみヒットする（`"moai"`はヒットしない） |
| `get_by_name()`は大文字小文字違いが共存してもエラーにならない (#1092) | 上記の状態で`get_by_name("MoAI")`と`get_by_name("moai")` | それぞれ対応するレコードを返す（`MultipleObjectsReturned`は発生しない） |
| `name__iexact`検索 (#1092) | `name="MoAI"`のauthorに対し`iexact="moai"`で検索 | 一致する |
| `name__icontains`検索 (#1092) | `name="MoAI Project"`のauthorに対し`icontains="moai"`で検索 | 一致する |

#### 11-3. `AuthorAlias` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| エイリアスの作成 | `AuthorAlias.objects.create(name="別名", author=author)` | DBに保存される |
| `name` のユニーク制約 | 同じ名前で2件作成（`alias_type`はgroup以外） | `IntegrityError` が発生 |
| `name__icontains`検索 (#1092) | `name="MoAI Alias"`のaliasに対し`icontains="moai"`で検索 | 一致する |
| `name=`によるexact matchは大文字小文字を区別する (#1092) | `"MoAI"`（author1）を作成後、`filter(name="moai")` | ヒットしない（`forms.py`の重複チェックが大文字小文字違いを誤って衝突と判定しないことの確認） |
| `alias_type` のデフォルト値 | `alias_type` 未指定で作成 | `alias_type == "another"` |
| `group`種別 (#1004) | `alias_type="group"`で作成 | DBに保存される。`CHOICES`に`"group"`が含まれる |
| `group`名の複数author登録 (#1044) | 同じ名前・`alias_type="group"`で別々のauthorが作成 | 両方ともDBに保存される（`(name, alias_type="group")`の組み合わせは複数authorで共有できる） |
| `group`名の同一author重複はブロック (#1044) | 同じauthorが同じ`group`名で2件作成 | `IntegrityError` が発生（`(name, author)`単位のユニーク制約） |
| `group`以外は引き続きグローバルにユニーク (#1044) | 同じ名前・`alias_type="spell"`等で別々のauthorが作成 | 2件目で`IntegrityError` が発生（従来通り） |

#### 11-3-1. `Author.get_effective_aliases()`（双方向解決ロジック）

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| 別名なし | 別名未登録のauthor | 空リストを返す |
| 対象authorが存在しない場合は単方向 | `author(foo)` に `name="foo_sub"` の別名を追加（`Author(foo_sub)` は未登録） | `foo.get_effective_aliases()` に正方向(`is_reverse=False`)の1件のみ |
| 対象authorが後から登録されると双方向になる | 上記に加え `Author.objects.create(name="foo_sub")` を作成 | `foo` 側は正方向のまま、`foo_sub.get_effective_aliases()` に逆方向(`is_reverse=True`, `name="foo"`)の1件が追加される |
| 正方向・逆方向の混在 | `foo` に正方向の別名、別author(`bar`)が `name="foo"` の別名を保持 | `foo.get_effective_aliases()` に正方向1件・逆方向1件の計2件 |
| 自分自身の別名は逆方向に二重計上しない | `foo` が `name="foo"`（自身の name と同じ値）の別名を1件保持 | 逆方向クエリが `exclude(author=self)` により同じaliasを除外し、正方向1件のみ（計1件） |

#### 11-3-2. `EffectiveAlias.alias_type_display`（#992）

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| CHOICESに存在する値 | `alias_type="past"` | `"以前の名称"` を返す |
| CHOICESに存在しない値 | `alias_type="unknown_type"` | 生の値をそのまま返す（フォールバック） |

#### 11-3-3. `Author.get_transitive_aliases()`（推移的関係解決ロジック、#1005）

具体例: 名義Aに「別名義B」「以前の名称C」「以前の名称D」「グループE」を登録した場合の5パターン全てを検証する。
`past`の関係は、正方向（自分がpastの別名を登録している側）では「以前の名称」、逆方向
（相手が自分をpastの別名として登録している側）では「その後の名称」と表示する（#1019）。

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| 別名なし | 別名未登録のauthor | 空リストを返す |
| Aの一覧 | `A.get_transitive_aliases()` | B(別名義,direct), C(以前の名称,direct), D(以前の名称,direct), E(所属グループ,direct) の4件 |
| Bの一覧 | `B.get_transitive_aliases()` | A(別名義,direct,reverse)の1件のみ。`another`は中継点にならないためC/D/Eには辿らない |
| Cの一覧 | `C.get_transitive_aliases()` | A(その後の名称,direct,reverse), B(別名義,indirect), D(以前の名称,indirect), E(所属グループ,indirect) の4件。`past`は中継点になるためAを経由してB/D/Eを発見する |
| Dの一覧 | `D.get_transitive_aliases()` | A(その後の名称,direct,reverse), B(別名義,indirect), C(以前の名称,indirect), E(所属グループ,indirect) の4件 |
| Eの一覧 | `E.get_transitive_aliases()` | A(所属している名義,direct,reverse)の1件のみ。`group`は中継点にならないためB/C/Dには辿らない |
| 循環関係の終端 | `x`↔`y`が互いに`spell`の別名を保持（閉路） | 訪問済みノードとして扱われ無限ループにならず、重複なく1件のみ返す |
| `TransitiveAlias.alias_type_display`（CHOICESに存在しない値） | `alias_type="unknown_type"` | 生の値をそのまま返す（フォールバック） |
| `TransitiveAlias.alias_type_display`（`past`・正方向、#1019） | `alias_type="past"`, `is_reverse=False` | `"以前の名称"` を返す |
| `TransitiveAlias.alias_type_display`（`past`・逆方向、#1019） | `alias_type="past"`, `is_reverse=True` | `"その後の名称"` を返す |
| `TransitiveAlias.author_id`（逆方向・正方向かつ中継可能、#1023） | AのA.get_transitive_aliases()でC/D（past、正方向）、CのC.get_transitive_aliases()でA（past、逆方向）等 | 追加クエリなしに解決済みのauthor idが設定される |
| `TransitiveAlias.author_id`（正方向かつ中継不可、#1023） | AのA.get_transitive_aliases()でB（another）・E（group）、CのC.get_transitive_aliases()でB・E（間接的） | `None`のまま（get_transitive_aliases()内では解決されない） |
| 同じグループ名を複数authorが共有する場合 (#1044) | 別々のauthor（x, y）が同じ名前・`alias_type="group"`の別名をそれぞれ登録 | `x.get_transitive_aliases()`にはxが登録した1件のみが表示され、`y.get_transitive_aliases()`にはyが登録した1件のみが表示される。`group`は中継不可のため、xの一覧からyの存在は辿れない（グループメンバー一覧UIは#1044のスコープ外として意図的に非対応） |

#### 11-4. `SongLink` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| リンクの作成 | `SongLink.objects.create(url="https://youtu.be/xxx")` | DBに保存される |
| `url` のユニーク制約 | 同じURLで2件作成 | `IntegrityError` が発生 |
| `url__iexact`検索 (#1092) | `url="https://youtu.be/AbCdEfGhIjK"`のlinkに対し小文字化した値で`iexact`検索 | 一致する |
| 曲との多対多関係 | `link.songs.add(song)` | 関係が成立する |

#### 11-5. `Contact` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `create_contact(detail)` | `Contact.create_contact("内容")` | レコードが作成され `post_time` が今日の日付になる |
| `get_answered()` | `answer` が空(`None`)のレコード | 結果に含まれない |
| `get_answered()` | `answer` が設定されたレコード | 結果に含まれる、`-id` 順 |

#### 11-6. `History` モデル（author向け拡張分、#991）

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `create_for_author()` | `History.create_for_author(author=author, ...)` | `history.author`が設定され`history.song`は`None`のまま |
| `create_for_song()` | `History.create_for_song(song=song, ...)` | `history.song`が設定され`history.author`は`None`のまま |
| authorの削除 | `create_for_author()`後に`author.delete()` | `history.author`が`None`になる（`on_delete=SET_NULL`、Historyレコード自体は残る） |
| `get_for_author(author)` | 複数authorのHistoryが存在する状態で対象authorを指定 | 対象authorのHistoryのみが`-create_time`順で返される |
| `create_for_song()`のtitle切り詰め (#1085) | `title`が200文字（`History.title`のmax_length=100超） | 保存されたtitleが100文字に切り詰められる（MySQL移行時のData too long for column対策。Song.titleを含む動的titleがHistory.titleの上限を超えうるため） |
| `create_for_author()`のtitle切り詰め (#1085) | `title`が200文字 | 保存されたtitleが100文字に切り詰められる |

#### 11-7. `Word` モデル（#1053）

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `__str__` | `Word(word="走る", hinshi="動詞", candidate="駆ける")` | `"走る(動詞) -> 駆ける"` を返す |
| `(word, hinshi, katsuyou, candidate)` のユニーク制約 | 同じ組み合わせで2件作成 | `IntegrityError` が発生 |
| `word != candidate` の CheckConstraint | `word`と`candidate`が同じ値で作成 | `IntegrityError` が発生（自己参照行の作成を防止） |
| `get_candidates(word, hinshi, katsuyou)` | 一致する候補が複数件登録済み | 候補一覧を返す |
| `get_candidates(word, hinshi, katsuyou)`（品詞不一致） | 別の品詞で登録された候補のみ存在 | 空リストを返す |
| `get_candidates(word, hinshi, katsuyou)`（活用形不一致） | 同じhinshiだがkatsuyouが異なる候補のみ存在 | 空リストを返す（文法破綻を防ぐため） |
| `get_candidates(word, hinshi, katsuyou)`（品詞・活用形ベース） | `word`が異なる他のWordの候補（同じhinshi・katsuyou） | wordを問わず候補プールに含めて返す |
| `get_candidates(word, hinshi, katsuyou)`（重複排除） | 異なるwordから同じcandidate文字列が存在 | 重複排除して返す |
| `get_candidates(word, hinshi, katsuyou, limit=10)` | 候補が11件以上登録済み | 最大10件に絞られる |
| `get_candidates(word, hinshi, katsuyou)`（ランダム性） | 候補が20件登録済みで20回呼び出す | 毎回同じ組み合わせにはならない（DB側の`ORDER BY RANDOM()`は使わず、hinshi・katsuyouで絞り込んだ結果をPython側の`random.shuffle()`でランダム化） |
| `get_candidates(word, hinshi, katsuyou)`（候補プールの上限） | distinct候補が`CANDIDATE_POOL_SIZE`（200件）を超えて登録済み | 全件をメモリに読み込まず、事前に打ち切ってから絞り込む（大きなhinshi・katsuyouの組み合わせでの性能懸念に対応） |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)` | 実在する組み合わせ | `True` を返す |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)` | 存在しない候補 | `False` を返す |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)` | 品詞が一致しない | `False` を返す |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)` | 品詞は一致するが活用形が異なる | `False` を返す（文法破綻を防ぐため） |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)`（品詞・活用形ベース） | `word`は異なるが`hinshi`・`katsuyou`が一致する候補 | `True` を返す |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)` | `get_candidates()`の表示上限（10件）を超える候補 | 実在すれば `True` を返す（表示件数の制限を受けない） |
| `is_valid_candidate(word, hinshi, katsuyou, candidate)`（自己参照） | `word == candidate` | DB上の実在有無に関わらず `False` を返す |

#### 11-8. `Ai` モデル（#593）

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `genetype="janome"`のlyricsユニーク制約 | 同じ`lyrics`・`genetype="janome"`で2件作成 | `IntegrityError` が発生（部分インデックス、MySQL移行時は要注意） |
| ユニーク制約はgenetype="janome"のみ対象 | 同じ`lyrics`だが`genetype`が異なる（例:`"model"`と`"janome"`） | `IntegrityError` は発生しない |
| `bulk_create(ignore_conflicts=True)`との組み合わせ | 既存の`genetype="janome"`レコードと同じ`lyrics`を含む複数件を`bulk_create` | 例外を投げず、重複する1件だけがスキップされ、他の正当な行は作成される |

#### 11-9. `Stats` モデル（月次統計、#334）

グラフが総合統計ページのsongrangeフィルターの影響を受けるように仕様変更（コードレビュー指摘対応）したため、`songrange`（all/subeana/xx）フィールドを追加し、月ごとに3件（songrangeの種類分）保存する構成に変更した。

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| デフォルト値 | `year`・`month`のみ指定して作成 | 各集計フィールドが`0`になる |
| `songrange`のデフォルト値 | `year`・`month`のみ指定して作成 | `songrange`が`"all"`になる |
| `(year, month, songrange)`のユニーク制約 | 同じ`year`・`month`・`songrange`で2件作成 | `IntegrityError`が発生 |
| `songrange`が異なれば同じ`(year, month)`でも作成可能 | `songrange="all"`と`songrange="subeana"`で同じ`(year, month)` | 2件とも作成できる |
| `__str__` | `year=2026, month=3, songrange="all"` | `"2026-03 (all)"` |
| `get_monthly_series()`の並び順 | 複数月のレコードを順不同で作成 | `year`, `month`昇順で返る |
| `get_monthly_series(songrange)`の絞り込み | `songrange="all"`と`songrange="subeana"`のレコードが混在 | 指定した`songrange`のレコードのみ返る |

---

### 12. `article` アプリ

**テストファイル**: `article/tests.py`

#### 12-1. `ArticlesView` (`/articles/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| タグフィルター | `?tag=news` | HTTP 200 |
| キーワード検索 | `?keyword=テスト記事タイトル` | HTTP 200、該当記事が含まれる |
| キーワード一致なし | 存在しないキーワード | HTTP 200 |
| タイトル中のリンクの除去（#483） | `tag="blog"`でタイトルが`[リンク](https://example.com)と**太字**` | 記事へのリンクの中で`<a>`が入れ子にならないよう、`リンクと<strong>太字</strong>`と表示される |

#### 12-2. `DefaultArticleView` (`/articles/<id>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する公開記事ID | 有効なarticle_id、`is_open=True` | HTTP 200 |
| 記事タイトルの表示 | 有効なarticle_id | レスポンスにタイトルが含まれる |
| マークダウンのタイトルの表示（#483） | `is_md=True`でタイトルが`**太字** & 記号` | 見出しは`<strong>太字</strong> &amp; 記号`、`<title>`はタグを除いた`太字 &amp; 記号` |
| 存在しない記事ID | 無効なarticle_id | HTTP 404 |
| 非公開記事 | `is_open=False` | HTTP 404 |
| 本文中の`<script>`へのnonce付与（#1126） | `is_md=False`で本文に`<script>`を含む | `<script nonce="（CSPヘッダーと同じnonce）">`として出力される |
| 本文が空 | `text=None` | HTTP 200 |
| マークダウンの画像を横スクロールの枠で囲む（#1167） | `is_md=True`で本文に`![画像](...)`を含む | `<span class="article-image"><img ... /></span>`として出力される |
| 画像の後の本文の保持（#1167） | `is_md=True`で画像2つの後に本文が続く | 各画像が`span.article-image`で囲まれ、画像の後の本文はそのまま出力される |
| HTMLで書かれた画像は囲まない（#1167） | `is_md=True`で本文に`<img>`タグを直接含む | `<img>`はそのまま出力され、`span.article-image`で囲まれない |
| HTML記事の画像は囲まない（#1167） | `is_md=False`で本文に`<img>`タグを含む | `<img>`はそのまま出力され、`span.article-image`で囲まれない |

#### 12-3. `is_pinned_article` Cookie による並び替え (`ArticlesView`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| Cookie未指定（デフォルトTrue） | `article_id="howToArticle"` の記事が存在 | 一覧の先頭が `howToArticle` になる |
| Cookie `is_pinned_article=False` | 同上 | `-post_time` 順のみで並び、`howToArticle` は先頭固定されない |

#### 12-4. `Article.get_top_news_articles()`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| `tag="news"` の記事 | 公開済み・投稿済み | 結果に含まれる |
| `tag="release"` の記事 | 公開済み・投稿済み | 結果に含まれる |
| `handle_as_news=True` の記事 | `tag="blog"` など他タグでも | 結果に含まれる |
| 上記以外のタグ | `handle_as_news=False` | 結果に含まれない |
| 非公開記事 | `is_open=False` | 結果に含まれない |
| 未来の`post_time` | `post_time` が未来日時 | 結果に含まれない |
| 件数上限 | 該当記事が5件 | 最大3件までに絞られる |
| 並び順 | 複数の該当記事 | `-post_time` の降順 |

#### 12-5. `Article.save()`・`Article.clean()`・`Article.__str__()` — タイトルのマークダウン変換（#483）

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| マークダウンのタイトル | `is_md=True`、`**太字**と[リンク](https://example.com)` | `<strong>太字</strong>と<a href="https://example.com">リンク</a>`に変換される |
| プレーンテキストのタイトル | `is_md=True` | 変わらない（`<p>`で囲まない） |
| HTMLで書かれた既存のタイトル | `is_md=True`、`<p><a ...>...</a>...</p>` | 変わらない |
| 変換後の再保存 | `is_md=True`で保存したあと再度`save()` | 1回目の変換結果から変わらない |
| HTMLの記事 | `is_md=False`、`**太字**` | 変換されない |
| 変換後の文字数が上限を超える | `is_md=True`、`**a**`×100（500文字） | `clean()`が`title`の`ValidationError`を送出する |
| HTMLの記事の文字数 | `is_md=False`、`**a**`×100（500文字） | 変換しないため、`clean()`は`ValidationError`を送出しない |
| `title_without_links` | タイトルにリンク・太字・`<br>`・アイコン（`<i>`）を含む | リンクの`<a>`タグだけが外れ、ほかのタグは残る |
| `__str__` | `is_md=True`、`**太字**の<br>タイトル & 記号` | タグを除いて文字参照を戻した`太字のタイトル & 記号`を返す（`plain_title`と同じ） |

#### 12-6. `article/lib/html_utils.py` の `remove_links(html)`（#483）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 属性値に`>`を含むリンク | `<a href="/x" title="a>b">リンク</a>の説明` | `リンクの説明`（タグの残骸が出ない） |
| 大文字のタグ | `<A HREF="/x">リンク</A>` | `リンク` |
| リンクの中のタグ | `<a href="/x">入れ子<strong>太字</strong></a>` | `入れ子<strong>太字</strong>` |
| リンクを含まないHTML | `<abbr>`・`<br>`・`<br/>`・`<i>`・文字参照・コメントを含む | 入力のまま変わらない |

---

### 13. `converters.py` — URLコンバータ

**テストファイル**: `tests/test_converters.py`

#### 13-1. `SQLiteIntConverter`

巨大な整数を含むURLアクセス時にSQLiteのINTEGER範囲を超えて`OverflowError`が発生していた不具合の修正に対応。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常の整数 | `"123"` | `123` を返す |
| SQLite INT最大値 | `str(9223372036854775807)` | そのまま返す |
| 最大値超過 | `str(9223372036854775808)` | `ValueError` が発生 |
| 巨大な数値 | `"9" * 30` | `ValueError` が発生 |
| `/songs/<id>/` への巨大なID | `"9" * 30` | HTTP 404（500エラーにならない） |

---

### 14. `management/commands` — 管理コマンド

**テストファイル**: `tests/test_management_commands.py`

#### 14-1. `delete` コマンド

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 通常削除 | `delete <id>` | Songが削除される |
| デフォルトの挙動 | `delete <id>` | 紐づく`SongLink.is_removed`が`True`になる |
| `--keep-links` 指定 | `delete <id> --keep-links` | `SongLink.is_removed`は`False`のまま |
| 存在しないID | `delete 999999` | 例外を投げず警告を出力 |

#### 14-2. `youtube` コマンド

DBロックエラー対策で全件処理時に先にID一覧を取得する方式に変更したことに対応（YouTube APIはモック化）。YouTube以外のURL（ニコニコ動画・SoundCloud等）は公開状況を確認できないため、それらを持つ曲はYouTubeの動画が全て取得不可でも`is_deleted`を変更しない（#1136）。また、YouTubeの動画が全て取得不可の場合、`view`・`like`・`upload_time`は前回の値を引き継ぐ（#1136）。APIの呼び出しに失敗した（`YoutubeApiError`）動画が1本でもある曲は、削除と区別して`is_deleted`・`view`・`like`・`upload_time`を更新しない。クォータ超過・APIキーの問題など以降の呼び出しも全て失敗する場合（`YoutubeApiUnavailableError`）は、残りの曲の処理を打ち切りDiscordにエラー通知する。存在しない`-id`を指定した場合は`CommandError`を送出し、全件処理中に削除された曲はスキップする（#1146）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| `-id` 指定 | 特定のSongのみ対象 | 指定Songのみ`view`等が更新される |
| `-id` 未指定 | SongLinkが紐づく全Song | 該当する全Songが更新される |
| SongLinkが無いSong | 対象外 | 更新されない（スキップ） |
| 全動画が取得不可 | `view`・`like`・`upload_time`が設定済み・`get_youtube_api` が `{}` を返す | `is_deleted=True` で保存され、`view`・`like`・`upload_time`は前回の値のまま |
| 全YouTube動画が取得不可＋YouTube以外のURLあり（#1136） | `view`・`like`・`upload_time`が設定済み・ニコニコ動画のURLも紐づく・`get_youtube_api` が `{}` を返す | `is_deleted=False` のまま、`view`・`like`・`upload_time`は前回の値のまま |
| 全YouTube動画が取得不可＋YouTube以外のURLあり＋手動で削除済み（#1136） | `is_deleted=True`・SoundCloudのURLも紐づく・`get_youtube_api` が `{}` を返す | `is_deleted=True` のまま |
| 複数YouTube動画のうち1つのみ取得可 | 1件目は `{}`、2件目は情報を返す | `is_deleted=False`、`view`は取得できた動画の値 |
| YouTube動画が取得可＋YouTube以外のURLあり（#1136） | ニコニコ動画のURLも紐づく・`get_youtube_api` が情報を返す | `is_deleted=False`、`view`は取得できた動画の値 |
| 手動で削除済み＋YouTube動画が取得可＋YouTube以外のURLあり（#1136） | `is_deleted=True`・ニコニコ動画のURLも紐づく・`get_youtube_api` が情報を返す | `is_deleted=False` に戻る |
| APIの呼び出しに失敗（#1146） | `view`・`like`・`upload_time`が設定済み・`get_youtube_api` が `YoutubeApiError` を送出 | `is_deleted=False` のまま、`view`・`like`・`upload_time`は前回の値のまま |
| 複数YouTube動画のうち1つが取得可・1つが呼び出し失敗（#1146） | 1件目は情報を返し、2件目は `YoutubeApiError` を送出 | 取得できた動画の値だけで更新せず、`view`・`like`・`upload_time`・`is_deleted`は前回の値のまま |
| 複数YouTube動画のうち1つが削除済み・1つが呼び出し失敗（#1146） | 1件目は `{}`、2件目は `YoutubeApiError` を送出 | 失敗した動画が公開されている可能性があるため、`is_deleted=False` のまま |
| 全件処理中に1曲だけ呼び出し失敗（#1146） | `-id` 未指定・1曲目の動画のみ `YoutubeApiError` を送出 | 処理を打ち切らず、失敗した曲のみ更新されず残りの曲は更新される。標準エラー出力に失敗した曲のIDが出る |
| クォータ超過（#1146） | `-id` 未指定・`get_youtube_api` が `YoutubeApiUnavailableError` を送出 | APIの呼び出しは1回で打ち切られ、どの曲も更新されない。Discord（`ERROR_DISCORD_URL`）と標準エラー出力に通知される |
| 2本目の動画でクォータ超過（#1146） | 1件目は情報を返し、2件目は `YoutubeApiUnavailableError` を送出 | 取得できた動画の値だけで更新せず、Discordに通知される |
| 存在しない `-id` 指定（#1146） | `-id 999999` | `CommandError` を送出し、APIは呼び出さない |
| 処理中に削除された曲（#1146） | `-id` 未指定・1曲目の処理中にもう1曲が削除される | 削除された曲はスキップし、例外を出さずに処理を終える |

#### 14-3. `backup` コマンド（バックアップ先をサーバーストレージからGoogle Driveに変更、#1050。MySQL移行対応でmysqldump方式を追加、#1086。ファイル名のJST化と`--now`オプションを追加、#1096）

サーバーのストレージにファイルを残さず、DBのダンプを一時ディレクトリに出力してGoogle Driveへアップロードする。`DATABASES['default']['ENGINE']`によりSQLite（`shutil.copy2`、拡張子`.sqlite3`）とMySQL（`mysqldump`、拡張子`.sql`）を切り替える。DATABASESは実行環境のUSE_MYSQL設定に依存するため、テストではSQLITE_DB_SETTINGS/MYSQL_DB_SETTINGSへ明示的に差し替えて両方式を検証する。Google Drive APIはモック化する。時刻取得はサーバーOSのタイムゾーン設定（本番はUTC）に依存する`datetime.now()`ではなく`timezone.localtime(timezone.now())`を使い、`config/settings.py`の`TIME_ZONE = 'Asia/Tokyo'`設定に基づきJSTでスケジュール判定・ファイル名生成を行う（#1096）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 実行対象外の時刻 | `now.hour`が6の倍数でない | アップロード・古いバックアップの削除のいずれも行われない |
| Drive認証情報未設定 | `GOOGLE_DRIVE_CLIENT_ID`等が空 | エラーメッセージを出力し、アップロードを行わない |
| JST基準の時刻取得（#1096回帰確認） | 実行後 | `timezone.localtime(timezone.now())`が呼ばれている（サーバーOSのタイムゾーンに依存する`datetime.now()`を使っていない） |
| SQLite: 実行対象の時刻・認証情報あり | `ENGINE=sqlite3`、`now.hour`が6の倍数 | `shutil.copy2`でDBファイルがコピーされ、`.sqlite3`拡張子・`mimetype="application/x-sqlite3"`でDriveにアップロードされた後、古いバックアップの削除（50件保持）が行われる |
| SQLite: ダンプファイルのパーミッション（コードレビュー対応） | コピー後 | DBダンプという機密性の高いファイルのため、`tempfile.TemporaryDirectory()`のumask依存パーミッションに任せず`os.chmod`で0600に明示的に絞る（Linux環境でのみ厳密に検証、Windowsの`os.chmod`は完全なUnixパーミッションを表現できないため） |
| SQLite: アップロード失敗時 | `upload_backup`が例外を送出 | エラーメッセージを出力し、古いバックアップの削除は行われない。`ERROR_DISCORD_URL`宛にDiscord通知を送る |
| SQLite: 削除失敗時 | アップロードは成功、`delete_old_backups`が例外を送出 | アップロード失敗時と異なる（削除専用の）エラーメッセージを出力し、Discord通知を送る |
| MySQL: 実行対象の時刻・認証情報あり | `ENGINE=mysql`、`now.hour`が6の倍数、`PORT`設定あり | `mysqldump --defaults-extra-file=<一時cnfファイル> --no-tablespaces --single-transaction --default-character-set=utf8mb4 --routines --events --triggers <NAME>`が実行され、標準出力がファイルに書き出される。`timeout=600`秒が設定される。`.sql`拡張子・`mimetype="text/plain"`でDriveにアップロードされる |
| MySQL: 認証情報の受け渡し方式（コードレビュー対応） | 実行後 | MySQL公式ドキュメントで非推奨とされる環境変数`MYSQL_PWD`は使わず、`--defaults-extra-file`で指定したパーミッション0600（Linux環境でのみ厳密に検証）の一時オプションファイル（`[client]`セクションに`user`/`password`/`host`/`port`を記載、ダブルクォート内は`\`と`"`をエスケープ）経由でホスト名・ユーザー名・パスワードを渡す。コマンドライン引数にはこれらが一切含まれない（DB名のみ残る）。オプションファイルは処理完了後（成功・失敗いずれの場合も）に削除される |
| MySQL: ダンプファイルのパーミッション（コードレビュー対応） | ダンプ出力後 | DBダンプという機密性の高いファイルのため、`os.chmod`で0600に明示的に絞る（Linux環境でのみ厳密に検証） |
| MySQL: `PORT`未設定 | `DATABASES['default']`に`PORT`キー自体が無い（`config/settings.py`はMYSQL_PORT未設定時にキーを含めない） | オプションファイルに`port=`行自体が含まれない |
| MySQL: mysqldumpコマンドが見つからない | `subprocess.run`が`FileNotFoundError`を送出 | SQLite同様「Google Driveへのバックアップ中にエラーが発生しました」に集約され、アップロード・古いバックアップの削除は行われない。一時オプションファイルはこの場合も削除される |
| MySQL: mysqldumpがエラー終了コードを返す | `returncode != 0` | サーバーの標準エラー出力（ログ）には`stderr`の詳細（ホスト名・ユーザー名等を含みうる）を出力しつつ、公開チャンネルである`ERROR_DISCORD_URL`宛のDiscord通知には一般化したメッセージ（exit codeのみ）のみを送る（詳細を含めない） |
| MySQL: mysqldumpがタイムアウトする | `subprocess.run`が`TimeoutExpired`を送出 | DBサイズの増加やネットワーク要因でハングした場合にバックアップジョブが無期限にブロックされないよう、他の失敗ケースと同様に「Google Driveへのバックアップ中にエラーが発生しました」に集約される。`TimeoutExpired.__str__()`は渡したcmdをそのまま文字列化するが、認証情報を`--defaults-extra-file`経由に変更したことでコマンド自体にはそもそもホスト名・ユーザー名・パスワードが含まれないため、公開チャンネルである`ERROR_DISCORD_URL`宛の通知にもこれらは含まれない |
| `--now`指定時: スケジュール・認証情報の無視（#1096） | 実行対象外の時刻・Drive認証情報未設定 | スケジュールガード・Drive認証チェックのいずれも行わず、ダンプの取得のみを行う |
| `--now`指定時: SQLiteの固定ファイル名ダンプ（#1096） | `ENGINE=sqlite3` | 日付・時刻ベースの可変ファイル名ではなく、固定ファイル名`subekashi_latest.sqlite3`でプロジェクトルート（`BASE_DIR`）にダンプが出力される。Google Driveへのアップロード・古いバックアップの削除は行われない |
| `--now`指定時: MySQLの固定ファイル名ダンプ（#1096） | `ENGINE=mysql` | 固定ファイル名`subekashi_latest.sql`で`mysqldump`によるダンプが出力される。Google Driveへのアップロード・古いバックアップの削除は行われない |
| `--now`指定時: ダンプ失敗時（#1096） | `mysqldump`が見つからない等でダンプが失敗 | エラーメッセージを出力するが、ローカル開発者による手動実行を想定しているため`ERROR_DISCORD_URL`宛のDiscord通知は送らない |
| `--now`指定時: 失敗時に直前のダンプを保持する（コードレビュー対応、#1096） | 固定パスに既存のダンプがある状態で`mysqldump`が失敗 | 固定パスへ直接書き込むのではなく`<固定パス>.tmp`に書き出してから成功時のみ`os.replace()`でアトミックに差し替えるため、失敗時は直前の正常なダンプがそのまま残り、一時ファイルも削除される（同期スクリプト等の読み取り側が書きかけの不完全なファイルを読んでしまうことも防ぐ） |

#### 14-4. `word` コマンド（`word.json`から模倣単語候補を`Word`に一括登録、#1053）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常なJSON | `[{"word":..., "hinshi":..., "candidates":[...]}]` | 各候補ごとに`Word`レコードが作成される |
| katsuyouの取り込み | エントリに`"katsuyou": "基本形"`を含む | `Word.katsuyou`に値が保存される |
| katsuyou未指定（旧形式） | エントリに`katsuyou`キーが無い | `Word.katsuyou`は空文字列になる（例外にならない） |
| 複数エントリ | 複数の単語エントリを含むJSON | 全エントリ分の候補がまとめて登録される |
| word/hinshiが空のエントリ | `word`または`hinshi`が空文字 | そのエントリはスキップされる |
| ファイルが存在しない場合 | `word.json`が無い | 例外を投げず、`CONST_ERROR`を出力（`python manage.py const`実行を促す） |
| 不正なJSON | パース不可能な内容 | 例外を投げず、`CONST_ERROR`を出力 |
| 再実行時の重複防止 | 同じ内容で2回実行 | `ignore_conflicts=True`によりレコードは重複作成されない |
| 完了メッセージの件数精度 | 同じ内容で2回実行 | 1回目は「新規Word候補数：1」、2回目（重複のみ）は「新規Word候補数：0」と、`count()`差分に基づく実際の新規作成数が表示される |
| `candidates`がlist以外 | `candidates`が文字列など | そのエントリは丸ごとスキップされる（文字列を1文字ずつ`Word`化してしまう事故を防止） |
| `candidates`内に文字列以外の要素 | `candidates`に数値・`null`が混在 | 文字列の要素のみ`Word`として登録され、それ以外は無視される |
| 自己参照エントリの除外 | `candidates`に`word`と同じ文字列が混在 | `CheckConstraint`のDB任せにせず、コマンド側で明示的に除外する（`bulk_create(ignore_conflicts=True)`のCHECK制約違反時の挙動がDBバックエンド依存のため） |
| トップレベルがlist以外 | JSONのトップレベルが`dict`など | 例外を投げず、`CONST_ERROR`を出力（`entry.get()`によるAttributeErrorを防止） |
| リスト内にdict以外の要素 | 文字列など`dict`でない要素を含むlist | その要素はスキップされ、他の正常なエントリのみ登録される |

#### 14-5. `ai` コマンド（`Song.lyrics`の単語入れ替えでgenetype="janome"のAiレコードをシード、#1053）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常なシード | 対象Songと一致するWord候補が存在 | `genetype="janome", score=0`のAiレコードが単語入れ替え済みの歌詞で作成される |
| ネタ動画（is_joke）は対象外 | `is_joke=True`のSongのみ存在 | Aiレコードは作成されない |
| 界隈曲か疑わしい曲（is_questionable）は対象外 | `is_questionable=True`のSongのみ存在 | Aiレコードは作成されない |
| 置き換え可能なトークンが無いSong | 該当するWord候補が1件も無い | 例外を投げずスキップされ、Aiレコードは作成されない |
| 7文字未満の結果は対象外 | 入れ替え後の歌詞が7文字未満 | Aiレコードは作成されない |
| 20文字超の結果は対象外 | 入れ替え後の歌詞が20文字超 | Aiレコードは作成されない |
| `--count`オプション | 対象Songが複数あり`--count 1`を指定 | 作成されるAiレコードは1件に絞られる |
| 再実行時の重複防止 | 同じ入れ替え結果になる状況で2回実行 | 既存レコードおよび今回の実行内の重複を除外し、`bulk_create`によりAiレコードは重複作成されない |
| 実行中の並行作成との競合耐性 | `existing_lyrics`のスナップショット取得後に、DB制約`unique_janome_lyrics`に抵触するlyricsが（別プロセス等により）先に存在する状況 | `ignore_conflicts=True`により、その1件だけがスキップされ、他の正当な新規レコードの`bulk_create`は失敗しない |
| 完了メッセージ | 正常なシード後 | 「新規Aiレコード数：N件（対象M曲中）」の形式で実際の件数を表示する |

#### 14-6. `stats` コマンド（月次統計(Stats)の集計・保存、#334。オプション廃止・常に全期間再計算、#1118）

`post_time`ではなく`upload_time`（YouTubeへのアップロード日時）基準で月を判定する。`upload_time=None`の曲は集計期間の起点判定・各月の集計いずれからも除外される。「現在時刻」の取得は`now_local()`（`timezone.localtime(timezone.now())`のラッパー）に統一し、サーバーOSのタイムゾーン設定に依存する素の`datetime.now()`は使わない（コードレビュー指摘対応）。総合統計ページのグラフがsongrangeフィルターの影響を受けるよう仕様変更したため、各月ごとにsongrange(all/subeana/xx)ごとの3件を集計・保存する（コードレビュー指摘対応）。

#1118で`--force`/`--year`/`--month`オプションを廃止し、旧`--force`の挙動（最古のSongの月〜今月までの全期間を再計算）を通常動作とした。これに伴い、旧仕様の「通常実行は当月分のみ」「月初(1日)のみ前月分も再計算」「直近`RETROACTIVE_LOOKBACK_DAYS`日以内に登録された曲のupload_time月を追加で再計算（#1106）」の各処理は削除された。全期間を毎回再計算するため、過去の年月に公開された動画を事後的に登録した場合（#1106）や、過去月の曲のview/likeが伸びた場合も、登録時期に関わらず次回実行時に自動で反映される。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 全期間を再計算 | 1月・3月にそれぞれ`upload_time`を持つSongが存在する状態で今月=3月15日として実行 | 曲の無い2月分も含め1月〜3月まで月ごとにall/subeana/xxの3件`Stats`が作成され、各月はその月末までの累積値になる。完了メッセージ「月次統計を更新しました。」が出力される |
| songrangeごとに正しく振り分けられる | is_subeana=True/Falseの曲が混在 | `songrange="subeana"`/`"xx"`のレコードがそれぞれの曲数のみを集計する |
| 年をまたいで再計算 | 前年12月に`upload_time`を持つSongが存在する状態で今月=1月1日として実行 | 前年12月分・当年1月分の両方が作成される |
| 曲が0件 | DBが空 | 集計期間の起点が決められないため何もせず終了する（`Stats`は作成されない） |
| `upload_time`を持つSongが1件も無い | 全曲`upload_time=None` | 同上 |
| `upload_time`未設定の曲は集計対象外 | `upload_time`を持つ曲と`upload_time=None`の曲が混在 | 例外にならず、`upload_time=None`の曲は`song_count`に含まれない |
| 事後登録された過去月の曲も反映（#1106） | 一度実行した後、`upload_time`が過去月(1月)・`post_time`が30日以上前の曲を追加して再実行 | 登録時期に関わらず1月分が作成され、当月分にも累積される |
| 過去月の値も最新化される（#1118） | 一度実行した後、過去月(1月)の曲のview/likeを更新して再実行 | 1月分の`total_view`/`total_like`が最新の値に更新される |
| 再実行時は上書き更新 | 既存の月・songrangeに対して再実行 | `update_or_create`により重複作成されず、値が最新の集計に更新される |
| 起点の月はローカルタイムゾーン基準 | `upload_time`がJST 2026-02-01 05:00（UTC 2026-01-31 20:00）の曲のみ存在 | 起点は2月となり、1月分は作成されない |
| `now_local()`を使用 | 正常実行 | `now_local()`が1回だけ呼ばれる |
| 廃止されたオプション（#1118） | `--year 2026 --month 1` | `CommandError`（オプションが存在しないため） |

#### 14-7. `sitemap` コマンド（sitemapの掲載ページを見直し、#970）

URL生成は`get_urls()`に分離しており、ファイル出力・`collectstatic`を伴わずにテストする。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 固定パス | 正常実行 | `/`・`/songs/`・`/songs/new/`・`/stats/`・`/ai/`・`/ai/result/`・`/ad/`・`/contact/`・`/articles/`・`/articles/lilyriku/`がそれぞれ1件ずつ含まれる（`/ai/`の重複を解消） |
| 曲・編集履歴 | 通常の曲が存在 | `/songs/<id>/`と`/songs/<id>/history/`が含まれる |
| noindexの曲は除外 | `is_questionable=True`または`is_limited=True`の曲が存在 | その曲の`/songs/<id>/`・`/songs/<id>/history/`は含まれない |
| 作者 | Authorが存在 | `/authors/<id>/`・`/authors/<id>/stats/`・`/authors/<id>/aliases/`が含まれ、存在しない旧パス`/author/<id>/`は含まれない |
| 旧形式のchannel | Authorが存在 | リダイレクト用の`/channel/<name>/`は含まれない |
| 記事 | 公開・非公開・news記事が混在 | 公開かつnews以外の記事のみ`/articles/<id>/`が含まれる |

---

### 15. `templatetags/song_card.py` — テンプレートタグ

**テストファイル**: `tests/test_templatetags_song_card.py`

#### 15-1. `get_author(song)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 作者0人 | `song.authors` が空 | 「作者不明」を表示 |
| 作者1人 | `song.authors` に1件 | 作者名と作者ページへのリンクを表示 |
| 作者2人以上 | `song.authors` に2件以上 | 「合作」を表示 |
| 作者名の特殊文字 | `name="<script>"` | HTMLエスケープされる |

---

### 16. `lib/author_alias_service.py` — 別名Discord通知・名義の統一サービス（#992、#1137）

**テストファイル**: `tests/test_lib_author_alias_service.py`

#### 16-1. `build_new_alias_discord_text(author, alias, editor)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 作者名を含む | 通常のauthor/alias | 戻り値に作者名が含まれる |
| 別名を含む | 通常のauthor/alias | 戻り値に別名が含まれる |
| 種別の表示名を含む | `alias_type="past"` | 戻り値に「以前の名称」が含まれる |
| 編集者を含む | 任意のeditor | 戻り値に編集者情報が含まれる |

#### 16-2. `build_edit_alias_discord_text(author, old_name, changes, editor)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| name変更を含む | `changes`に`["別名", 旧, 新]`を含む | 戻り値に変更前・変更後の別名が含まれる |
| alias_type変更を含む | `changes`に`["種別", 旧, 新]`を含む | 戻り値に変更前・変更後の種別表示名が含まれる |
| 作者名を含む | 通常のauthor | 戻り値に作者名が含まれる |

#### 16-3. `build_delete_alias_discord_text(author, alias_name, editor)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 作者名を含む | 通常のauthor | 戻り値に作者名が含まれる |
| 別名を含む | 任意のalias_name | 戻り値に別名が含まれる |

#### 16-4. `build_unify_name_plan(author, new_name)`（#1137）

名義の統一で行う変更内容（`UnifyNamePlan`）を算出する。DBアクセスを伴うため `TestCase` を使用する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 現在の名前を選択 | `new_name=author.name`、past別名と同名のAuthorが存在 | `target_author`はauthor自身、`source_authors`はpast別名と同名のAuthor。`renames_author`・`moves_to_existing_author`ともに`False` |
| 同名のAuthorがないpast別名を選択 | `new_name=`past別名のname | `target_author`はauthor自身、`source_authors`は空、`renames_author=True` |
| 同名のAuthorがあるpast別名を選択 | `new_name=`past別名のname、同名のAuthorが存在 | `target_author`はその既存Author、`source_authors`はauthor自身、`moves_to_existing_author=True` |
| past以外の別名と同名のAuthorは対象外 | `another`別名と同名のAuthorが存在 | `source_authors`に含まれない |
| `song_author_pairs()`・`affected_source_authors()` | past別名と同名のAuthorのうち、一方だけがSongを持つ | `song_author_pairs()`は`(song_id, author_id)`の一覧を返し、`affected_source_authors()`は曲を持つAuthorのみを返す |
| 統一先が既存Authorの場合の`affected_source_authors()` | 統一先が既存Authorで、authorがSongを持たない | 別名・リンクを移すため、曲が無くてもauthor自身が含まれる |

#### 16-5. `build_unify_name_discord_text(target_author, old_name, new_name, editor, source_authors=())`（#1137）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 統一後の名義・統一先の別名一覧URLを含む | 通常の呼び出し | 戻り値に`new_name`と`/authors/<target_author.id>/aliases`が含まれる |
| 変更前の名義は変わった場合のみ含む | `old_name != new_name` / `old_name == new_name` | 前者は`old_name`を含み、後者は「変更前」を含まない |
| 統一元を含む | `source_authors`を指定 | 戻り値に`Author(id=<id>, name=<name>)`が含まれる |
| 編集者を含む | 任意のeditor | 戻り値に編集者情報が含まれる |

---

### 17. `lib/google_drive.py` — Google Driveバックアップ連携（#1050）

**テストファイル**: `tests/test_lib_google_drive.py`

Google Drive APIはモック化する。

#### 17-1. `upload_backup(file_path, file_name, mimetype="application/x-sqlite3")`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| アップロード先の指定 | 通常のファイルパス・ファイル名 | 指定したファイル名・フォルダIDでアップロードが実行される |
| アップロード後のファイルハンドル解放 | アップロード実行後 | 元ファイルを削除できる（ハンドルが残っていない） |
| mimetype省略時のデフォルト（#1086） | `mimetype`引数なし | `application/x-sqlite3`でアップロードされる |
| mimetype指定時（#1086） | `mimetype="text/plain"`（mysqldumpダンプ用。`application/sql`はIANA未登録のため使用しない） | 指定したmimetypeでアップロードされる |

#### 17-2. `delete_old_backups(keep_nums)` — 保持件数の境界値

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 保持件数未満 | ファイル数 < `keep_nums` | 削除されない |
| 保持件数未満だが半数超過（#1086、実際に本番で発生したバグの回帰防止） | `keep_nums / 2 < ファイル数 < keep_nums`（例: 26件、`keep_nums=50`） | 削除されない。`len(files) - keep_nums`が負の場合に`max(0, ...)`でクランプしていないと、`files[:負の数]`が末尾からの相対指定と解釈され、意図せず先頭（最も古い）ファイルが削除されてしまう |
| 保持件数ちょうど | ファイル数 == `keep_nums` | 削除されない |
| 保持件数を1件超過 | ファイル数 == `keep_nums + 1` | 最も古い1件のみ削除される |
| 保持件数を複数件超過 | ファイル数 > `keep_nums + 1` | 超過分がすべて（古い順に）削除される |

---

### 18. `lib/lyric_tokenizer.py` — 歌詞の単語分割（#1053）

**テストファイル**: `tests/test_lib_lyric_tokenizer.py`

#### 18-1. `tokenize_lyrics_with_index(lyrics)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 単語分割 | `"私は走る"` | `surface`が`["私", "は", "走る"]`に分割される |
| 連番index付与 | `"私は走る"` | 各トークンに`0, 1, 2`の`index`が付与される |
| 品詞の大分類 | `"私は走る"` | `私`→`名詞`, `は`→`助詞`, `走る`→`動詞` |
| 動詞・形容詞のkatsuyou | `"私は走る"`, `"とても嬉しい"` | 活用形（`infl_form`）を返す（例:「基本形」）。SubeteJanomeNoSeidesu側の規約と一致させる必要がある |
| 名詞のkatsuyou | `"犬"` | 品詞細分類のフル文字列（`part_of_speech`）を返す（例:「名詞,一般,\*,\*」） |
| それ以外のkatsuyou | `"私は走る"`の`は` | 空文字列を返す |

#### 18-2. `tokenize_ai_instances(ai_queryset)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 候補が存在する単語 | 該当する`Word`が登録済み | `is_replaceable=True` |
| 候補が存在しない単語 | `Word`未登録 | `is_replaceable=False` |
| 置き換え対象外の品詞 | 助詞など`REPLACEABLE_HINSHIS`外 | 同表記の`Word`が存在しても`is_replaceable=False` |
| 品詞をまたいだ候補の誤判定防止 | 別品詞で同じ表記の`Word`のみ存在 | `is_replaceable=False`（品詞の組み合わせで厳密一致） |
| katsuyou不一致でもis_replaceableはTrue（既知の許容範囲） | `(word, hinshi)`は一致するがkatsuyouが異なる`Word`のみ存在 | `is_replaceable=True`になる一方、`Word.get_candidates()`は空リストを返す（`word_swap.js`側で「候補が見つかりません」として吸収） |
| 結果の`id`・`lyrics` | `Ai`インスタンスを渡す | 各要素に`id`・`lyrics`が含まれる |
| 空のqueryset | `Ai.objects.none()` | 空リストを返す |
| 副詞は置き換え対象（SubeteJanomeNoSeidesu側との整合、#1048） | 副詞に該当する`Word`が登録済み | `is_replaceable=True` |
| 連体詞は置き換え対象（SubeteJanomeNoSeidesu側との整合、#1048） | 連体詞に該当する`Word`が登録済み | `is_replaceable=True` |

---

### 19. `lib/stats_service.py` — 統計集計ユーティリティ（#334）

**テストファイル**: `tests/test_lib_stats_service.py`

総合統計ページ・authorごとの統計ページ・`stats`管理コマンドが共通で使う集計ロジック。

#### 19-1. `apply_songrange_filter(qs, songrange)` / `apply_upload_time_filter(qs, year, month)`

`apply_upload_time_filter`は`post_time`ではなく`upload_time`（YouTubeへのアップロード日時）基準で絞り込む（#334）。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| `songrange="all"` | 任意のqs | 絞り込まれない |
| `songrange="subeana"` | 任意のqs | `is_subeana=True`のみ |
| `songrange="xx"` | 任意のqs | `is_subeana=False`のみ |
| `year="all"` | 任意のqs | 絞り込まれない |
| `year`のみ指定 | `year="2024"`, `month="all"` | `upload_time`の年のみで絞り込み |
| `year`・`month`両方指定 | `year="2024"`, `month="6"` | `upload_time`の年月両方で絞り込み |
| `year="all"`でも`month`のみ指定 | `year="all"`, `month="1"` | yearと独立してmonthのみで絞り込み、年をまたいだ該当月の曲が全て対象になる（#334で年月セレクトの独立表示に変更） |
| `upload_time=None`の曲 | `year`を指定 | 対象外になる（SQLのNULL比較により除外） |
| `upload_time=None`の曲 | `year="all"`で`month`のみ指定 | 対象外になる |

#### 19-1-1. `get_songrange_availability(qs)`（#334）

is_subeana=True/Falseの曲がqs内にそれぞれ存在するかを返す。両方存在しない場合、"全て"の選択肢を非表示にする判定に使う。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 両方存在 | is_subeana=True/Falseの曲がそれぞれ1件以上 | `(True, True)` |
| subeanaのみ存在 | is_subeana=Trueの曲のみ | `(True, False)` |
| xxのみ存在 | is_subeana=Falseの曲のみ | `(False, True)` |
| どちらも存在しない | 曲が0件 | `(False, False)` |

#### 19-1-1-1. `resolve_songrange(request, base_qs)`（#334、コードレビュー指摘対応）

`StatsView`/`AuthorStatsView`でほぼ同一だったsongrangeのGETパラメータ検証・正規化ロジック（不正値のフォールバック・選択肢が1つしかない場合の強制解決）を共通化したもの。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 両方存在する場合はそのまま | is_subeana=True/Falseの曲がそれぞれ存在、songrange未指定 | `("all", True)` |
| 不正な値は"all"にフォールバック | `?songrange=invalid` | `"all"` |
| 片方しか無い場合は強制解決 | is_subeana=Trueの曲のみ存在、songrange未指定 | `("subeana", False)` |
| 片方しか無い場合は明示指定も上書き | is_subeana=Trueの曲のみ存在、`?songrange=xx` | `"subeana"`に上書きされる |

`compute_common_stats`/`compute_unique_author_count`/`compute_total_imitates`/`compute_collaborator_count`/`compute_unique_collaborator_count`は絞り込み済みのQuerySet`qs`をそのまま受け取る。内部の`_clean_base(qs)`が`Song.objects.filter(id__in=qs.values("id"))`としてid一覧をサブクエリ化した上でM2Mの`annotate(Count(...))`を重ねるため、`qs`側に既に乗っているJOINとのfan-outを避けつつ、idをPythonリストへ列挙しない（曲数が増えてもSQLiteのバインド変数上限に触れない、コードレビュー指摘対応）。

#### 19-1-1-2. `resolve_year_month(request, year_choice_qs=None)`（#334、コードレビュー指摘対応）

`StatsView`/`AuthorStatsView`でほぼ同一だったyear/monthのGETパラメータ検証・正規化ロジック（`parse_int_or_none`によるバリデーション、ゼロ埋め等の正規化、選択肢`year_choices`/`month_choices`の算出）を共通化したもの。`year_choice_qs`を渡すことで、author自身の曲・選択中のsongrangeなど実際に選択可能な年・月のみに`year_choices`/`month_choices`を絞り込める（省略時はサイト全体が対象、コードレビュー指摘対応: 選択肢に「選んでも0件になる年/月」が含まれてしまう問題の修正）。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| デフォルト（曲が0件） | GETパラメータ無し、DBが空 | `("all", "all", [], [])` |
| ゼロ埋めの正規化 | `?year=02024`、該当する曲が存在 | `year`が`"2024"`に正規化される |
| 数値でないyear | `?year=abc` | `year`は`"all"`にフォールバックする |
| month_choicesも実データに連動（コードレビュー指摘対応） | 3月に曲が存在、他の月は存在しない | `month_choices`が`[3]`になる |
| `year_choice_qs`で選択肢を絞り込める | 範囲外の曲と範囲内の曲が混在 | `year_choices`が範囲内の曲の年のみになる |

#### 19-1-2. `parse_int_or_none(value)`（#334、コードレビュー指摘対応）

`?year=abc`のような数値変換できないGETパラメータを渡された際に`int()`が`ValueError`を送出し500エラーになる不具合の修正で追加。ビュー側のyear/monthバリデーションで使用する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 数値文字列 | `"2024"` | `2024` |
| 数値でない文字列 | `"abc"` | `None` |
| 小数文字列 | `"1.5"` | `None` |
| `None` | `None` | `None` |
| 空文字列 | `""` | `None` |

#### 19-1-3. `now_local()`（#334、コードレビュー指摘対応）

`stats`コマンド内で`datetime.now()`（サーバーOSのタイムゾーン設定に依存）と`timezone.localtime()`（Djangoの設定タイムゾーン基準）が混在していたことによるタイムゾーン不整合の修正で追加。`timezone.localtime(timezone.now())`のラッパーで、Djangoの`TIME_ZONE`設定を常に使う。`get_year_choices()`/`get_month_choices()`・`StatsView`/`AuthorStatsView`の`current_year`計算でも、同種のズレ防止のため`timezone.now()`の代わりにこちらを使う（コードレビュー指摘対応）。

| テストケース | 期待結果 |
| --- | --- |
| 呼び出し直後の値 | timezone-aware、`timezone.now()`呼び出し前後の時刻範囲内に収まる |

#### 19-2. `compute_view_like_totals(qs)` / `get_view_like_pairs(qs)` / `compute_base_stats(qs)` / `compute_common_stats(qs)`

`compute_view_like_totals`はsong_count/total_view/total_likeのみを返す最小構成（total_imitateds/total_authorsを含まない）。`get_view_like_pairs`はqs内の各曲のview/likeを`(view, like)`のペアのリストとして列挙する（Noneは0扱い）。鍵歴（#968、`kenreki_service.py`参照）はSongごとに算出してから合計する仕様のため、集計済みのSumではなくこちらを使う。`compute_base_stats`は`compute_view_like_totals`に`total_imitateds`を加えたもの、`compute_common_stats`はさらに`total_authors`（`compute_unique_author_count`によるAuthor起点の追加クエリ）を加えたもので、総合統計ページ・stats管理コマンドのみが使う。authorごとの統計ページはtotal_authorsを画面に表示しない（合作人数を別途算出するため）ため`compute_base_stats`を使い、無駄なクエリが発行されないようにしている（コードレビュー指摘対応）。

| テストケース | 対象 | 前提条件 | 期待結果 |
| --- | --- | --- | --- |
| 空のqueryset | `compute_view_like_totals` | 曲が0件 | 全フィールドが0 |
| view/likeがNullな曲を含む | `compute_view_like_totals` | 一部の曲の`view`・`like`が`None` | `Sum`が`None`にならず0として扱われる |
| 空のqueryset | `get_view_like_pairs` | 曲が0件 | `[]` |
| 曲ごとのペアを返す | `get_view_like_pairs` | 曲1(view=100,like=10)・曲2(view=5,like=1) | `[(100, 10), (5, 1)]` |
| view/likeがNullな曲 | `get_view_like_pairs` | `view=None, like=None` | `(0, 0)`として扱われる |
| 空のqueryset | `compute_base_stats` | 曲が0件 | 全フィールドが0 |
| view/likeがNullな曲を含む | `compute_base_stats` | 一部の曲の`view`・`like`が`None` | `Sum`が`None`にならず0として扱われる |
| 模倣されている曲 | `compute_base_stats` | 2曲がある曲を模倣 | `total_imitateds`がその曲について2になる |
| 同じ作者が複数曲に関わる | `compute_common_stats` | 作者Aが2曲、作者Bが1曲（Aと共作） | `total_authors`は重複を除いた人数（2）になる（`compute_unique_author_count`を内部で使用、#334で`song.authors`の総和から変更） |
| 作者数と模倣曲数の相互干渉防止（回帰） | `compute_common_stats` | 複数作者かつ複数の模倣曲を同時に持つ曲 | `total_authors`（Authorテーブル起点のユニーク集計）と`total_imitateds`（Songテーブル起点のCount集計）が互いに水増しされず、それぞれ正しい値になる |

`AuthorStatsView`側では、これらの分離によりtotal_authors/total_imitateds算出の無駄なクエリが発行されないことをクエリ数のアサーション（`test_does_not_issue_unused_total_authors_query`、`tests/test_views.py`）で回帰防止している。

#### 19-2-1. `build_stats_items(stats, items)`（#334、コードレビュー指摘対応）

`{% if item.value %}`による0/None非表示が「曲が0件（データなし）」と「曲は存在するが特定の指標だけ0（実際の値）」を区別していなかった問題の修正で追加。`stats["song_count"]`が0の場合のみ空リスト（統計カード全体を非表示）を返し、それ以外は`items`をそのまま返す（個々の値が0でもテンプレート側では表示する）。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| song_countが0 | `stats["song_count"] == 0` | 空リストを返す |
| song_countが0以外 | `stats["song_count"] >= 1`、`items`内に値0の項目を含む | `items`をそのまま返す（値0の項目も含めて） |

#### 19-3. `compute_unique_author_count(qs)` / `compute_total_imitates(qs)`

`compute_unique_author_count`は`compute_common_stats`内部で`total_authors`の算出にも使われる。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 同一作者が複数曲を持つ | 2曲が同じ作者 | ユニーク作者数は1 |
| 空のqueryset | 曲が0件 | 0 |
| 複数の原曲を模倣 | 1曲が2曲を模倣 | `compute_total_imitates`が2 |

#### 19-3-1. `compute_collaborator_count(qs, author_id)` / `compute_unique_collaborator_count(qs, author_id)`（authorごとの統計ページのみ、#334）

「合作人数(重複あり)」「合作人数(重複なし)」の算出に使用。いずれも`author_id`本人を除いて数える。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 本人以外の作者数の総和（重複あり） | 本人+他2名の曲、本人のみの曲、本人+他1名の曲 | `compute_collaborator_count`が3（2+0+1） |
| 本人のみの曲だけ | 共作者なし | `compute_collaborator_count`が0 |
| 本人以外のユニーク数 | 上記と同じ前提 | `compute_unique_collaborator_count`が2（重複する共作者は1人として数える） |
| 本人のみの曲だけ | 共作者なし | `compute_unique_collaborator_count`が0 |

#### 19-4. `get_year_choices(qs=None)` / `get_month_choices(qs, year=None)`

いずれも単純な日付計算（最古年〜今年の連続レンジ、1〜12月 or 1〜現在月）ではなく、`qs`内で実際に`upload_time`が存在する年・月のみを返すデータ駆動の実装（コードレビュー指摘対応: 間の年/その年に投稿の無い月も連続レンジ・固定リストとして選択肢に出てしまい、選ぶと0件になる問題の修正。特にauthorページで顕著）。`ExtractYear`/`ExtractMonth`はDjangoのタイムゾーン設定に従って変換されるため、DBがUTC保存でもローカルタイムゾーン基準で年月が判定される。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 曲が0件 | DBが空 | `get_year_choices()`は空リスト |
| `upload_time`を持つ曲が0件 | 全曲`upload_time=None` | `get_year_choices()`は空リスト |
| 投稿の無い間の年は選択肢に出ない（コードレビュー指摘対応） | 2020年・2024年にのみ曲が存在（2021〜2023年は無し） | `[2020, 2024]`（連続レンジの`[2020, 2021, ..., 2024]`にはならない） |
| `qs`引数で範囲を絞り込める（コードレビュー指摘対応） | 範囲外の曲と範囲内の曲が混在 | 範囲外の曲の年は無視され、範囲内の曲が実際に存在する年のみ返る |
| 年の判定はローカルタイムゾーン基準（回帰） | `upload_time`がUTC 2019-12-31 20:00（JST 2020-01-01 05:00） | `[2020]`になる（`[2019]`にならない） |
| yearを指定すると実際に曲が存在する月のみ返す（コードレビュー指摘対応） | 1月・6月に曲があり、他は無い年を指定 | `[1, 6]` |
| yearを指定しない場合は年を問わず全期間が対象 | 年をまたいで複数の月に曲が存在 | 年に関わらず該当する月のリストを返す |
| 曲が存在しない年を指定 | その年には曲が無い | 空リスト |
| `qs`で範囲を絞り込める | 範囲外の曲と範囲内の曲が混在 | 範囲外の曲の月は無視される |

#### 19-5. `next_year_month(year, month)` / `month_start(year, month)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常の月送り | `next_year_month(2026, 3)` | `(2026, 4)` |
| 12月からの繰り上げ | `next_year_month(2026, 12)` | `(2027, 1)` |
| タイムゾーン付きdatetime | `month_start(2026, 3)` | ローカルタイムゾーンで2026年3月1日を指すaware datetimeを返す |

#### 19-6. `with_monthly_deltas(rows)` / `filter_monthly_series_by_year_month(rows, year, month)`（#334、コードレビュー指摘対応）

総合統計ページのグラフをsongrange/year/monthフィルターに連動させる仕様変更で追加。`with_monthly_deltas`は累積値の行リストから各フィールドの単月差分(`<field>_delta`)を計算し、`filter_monthly_series_by_year_month`は表示するyear/monthの行に絞り込む。差分計算は絞り込み前の全期間に対して行ってから絞り込むため、表示範囲を狭めても差分値はずれない。

`filter_monthly_series_by_year_month`は`year`が指定されている場合はその年のみに絞り込み、`month`による絞り込みは行わない（コードレビュー指摘対応: year・monthを両方指定すると棒グラフが1本だけになり意味を成さないため、その年の全期間を表示するよう変更。以前は両方適用され1本になっていた）。`year="all"`の場合は`month`のみで独立して絞り込める（年をまたいだ同月比較として意味を成す）。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 先頭行の差分 | 1件のみの行リスト | 累積値そのものが差分になる |
| 2件目以降の差分 | 2件の行リスト | 直前の行との差分になる |
| 累積値は保持される | 任意の行リスト | 元の`<field>`キー（累積値）はそのまま残る |
| 空リスト | `[]` | `[]` |
| `year="all"` | 任意の行リスト | 絞り込まれない |
| `year`のみ指定 | 複数年の行リスト | 該当年の行のみ |
| `year`・`month`両方指定（コードレビュー指摘対応） | 複数年月の行リスト | `month`は無視され、該当年の全期間が表示される |
| `year="all"`でも`month`のみ指定（回帰、コードレビュー指摘対応） | 複数年の行リスト、`month`のみ指定 | yearに関わらず該当月の行が年をまたいで全て残る |

---

### 20. `lib/kenreki_service.py` — 鍵歴（実績鍵盤）算出ユーティリティ（#968。2pt=鍵盤1本の換算を廃止、#1099）

**テストファイル**: `tests/test_lib_kenreki_service.py`

「鍵歴」（総再生回数・総高評価数の実績に応じて伸びる鍵盤）の算出ロジック。総合統計ページ・authorごとの統計ページ両方の`stat-item`として表示するが、鍵盤ビジュアル（`components/kenreki.html`）はauthorごとの統計ページのみに表示する（コードレビュー指摘対応で総合統計ページにも追加、鍵盤は不要とのことでstat-itemのみ）。

鍵歴はSongごとに算出してから合計する仕様（コードレビュー指摘対応: 当初はauthor/サイト全体の集計値(Sum)にまとめて閾値判定していたが、Songごとに算出してその総和を表示する方式に変更。同じ合計viewでも曲数が多いほど有利になる）。`get_view_like_pairs(qs)`（`lib/stats_service.py`）でqs内の各曲のview/likeペアを取得し、`compute_kenreki_for_songs`に渡す。

- authorごとの統計ページ: songrange/year/monthの絞り込みの影響を受けない、authorの全期間・全曲（`AuthorStatsView`では`get_view_like_pairs(author_songs)`で取得、`tests/test_views.py`の`test_kenreki_not_affected_by_songrange_year_month_filters`で回帰防止）
- 総合統計ページ: 他の統計項目と同様、絞り込みの影響を受ける（`StatsView`では`get_view_like_pairs(qs)`で取得、`tests/test_views.py`の`test_kenreki_reflects_songrange_year_month_filters`で回帰防止）。stat-valueの着色はしない（`overflow_color`を`None`に上書き、`test_kenreki_stat_value_never_colored_even_when_overflowing`で回帰防止）

`points`（pt合計）はそのまま鍵盤本数としても扱う（#1099で`POINTS_PER_KEY`による2pt=鍵盤1本の換算を廃止。従来は`stat-item`の表示・鍵盤ビジュアルの両方が別フィールドの`key_count`(pt合計を2で割った値)を使っており、pt合計が奇数だと表示上端数が切り捨てられていた）。換算を廃止した結果`points`と`key_count`が常に同値になり、フィールドを分ける意味が無くなったため、`key_count`は`_kenreki_from_points`の返り値から削除し、鍵盤ビジュアル（`AuthorStatsView`が`build_keyboard_geometry`に渡す引数）・画面表示（`components/stats_summary.html`・`author.html`）ともに`points`を直接使うよう統一した（#1099フォローアップ）。`tests/test_views.py`の`test_kenreki_stat_value_displays_points_not_song_count_stat`（`StatsViewTest`/`AuthorStatsViewTest`）・`test_stats_summary_shows_kenreki`（`AuthorViewTest`）で回帰防止。

#### 20-1. `compute_threshold_points(value, thresholds)`

`VIEW_THRESHOLDS`（1, 20, 50, 100, 200, 500, ...）・`LIKE_THRESHOLDS`（1, 2, 5, 10, 20, 50, ...）のうちvalueが到達した段階数を、そのままptとして返す（コードレビュー指摘対応: 当初は各段階に到達順で1, 2, 3, ...ptを割り当てその累計〔三角数〕を返していたが、これはユーザーの意図と異なる実装ミスだった。正しくは到達した段階数そのものがpt。例えばthresholdsが`[1, 20, 50, 100, ...]`でvalue=55なら、1・20・50の3段階に到達しているため3pt）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 最初の閾値未満 | `value`が`thresholds[0]`未満 | 0 |
| 1段階目のみ到達 | `value`が1段階目以上2段階目未満 | 1 |
| 複数段階に到達 | `value`が3段階目まで到達（4段階目未満） | 3 |
| 閾値の間の値 | 到達済み段階数はそのまま、次段階未満 | 到達済み段階数のまま変化しない |
| 全段階到達 | `value`が最終閾値以上 | `len(thresholds)`（全段階数） |

#### 20-2. `compute_song_points(view, like)`（1曲分のpt）

`compute_threshold_points`のview側・like側の結果を単純に加算する（1曲分の鍵歴pt）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| view・likeの合算 | view=20(2段階=2pt)、like=2(2段階=2pt) | 4pt |
| view・like共に0 | `(0, 0)` | 0pt |

#### 20-3. `compute_kenreki(view, like)`（1曲分）/ `compute_kenreki_for_songs(view_like_pairs)`（複数曲の総和）

`compute_kenreki`は`compute_song_points`の結果から1曲分の鍵歴を算出する。`compute_kenreki_for_songs`は`(view, like)`のリストを受け取り、各曲の`compute_song_points`を合計してからオーバーフロー色等に変換する（authorごとの統計・総合統計ページで表示するのはこちら）。

両者とも共通の変換処理（`_kenreki_from_points`）を通す。返り値の`points`（pt合計）自体はカンストさせず実際の達成数をそのまま返す（鍵盤ビジュアルの描画本数のみ`MAX_KEYS`を上限とし、呼び出し側で`min(points, MAX_KEYS)`してから`build_keyboard_geometry`に渡す）。`points`が`MAX_KEYS`(88、現実のピアノの鍵盤数)以上になった時点で、`MAX_POSSIBLE_KEY_COUNT`（2pt=1鍵盤換算を廃止する前の実データ最大値1,506相当のpt換算後のおおよその最大値に対して、十分な伸びしろを持たせた固定値5,000、都度DBクエリはしない）に対する超過度合いを虹色（赤hue=0〜紫hue=270）のHSL色相に連続的にマッピングし、`overflow_color`として返す（`MAX_KEYS`未満なら`None`）。`overflow_lower_bound`(=`MAX_KEYS`)は常に結果に含まれるが、`overflow_upper_bound`(=`MAX_POSSIBLE_KEY_COUNT`)は超過時のみ値が入り、非超過時は`None`（スペクトル表示は超過時のみ描画するため）。

現行の閾値表で1曲あたり到達しうる理論上の最大pt（`MAX_TOTAL_POINTS` = view22段階+like21段階 = 43pt）は`MAX_KEYS`(88)にも届かないため、**1曲だけではMAX_KEYSに到達できず色分岐は発生しない**（複数曲の総和で初めてMAX_KEYSを超えうる、意図した設計）。

| テストケース | 対象 | 条件 | 期待結果 |
| --- | --- | --- | --- |
| view・like共に0 | `compute_kenreki` | `(0, 0)` | `points=0`, `overflow_color=None`, `overflow_upper_bound=None` |
| compute_song_pointsと一致 | `compute_kenreki` | view=20、like=2 | `points=4` |
| 1曲だけではMAX_KEYSに届かない | `compute_kenreki` | view・likeとも全閾値到達（43pt） | `points=43`（< MAX_KEYS）、`overflow_color=None` |
| 空リスト | `compute_kenreki_for_songs` | `[]` | `points=0` |
| 1曲のみ | `compute_kenreki_for_songs` | `[(20, 2)]` | `compute_kenreki(20, 2)`と同じ結果 |
| 複数曲のpt合計 | `compute_kenreki_for_songs` | 各曲view=1(1pt)を3曲 | `points=3` |
| 曲数が多いほど有利（回帰） | `compute_kenreki_for_songs` | view=1の曲10本 vs view=10の曲1本 | 前者の方が合計pt(10pt)が後者(1pt)より高い（同じ合計viewでも曲を分けた方が有利） |
| MAX_KEYS未満（複数曲） | `compute_kenreki_for_songs` | 全閾値到達の曲を2曲（86pt） | `points=86`、`overflow_color=None` |
| MAX_KEYS以上で色分岐開始（複数曲） | `compute_kenreki_for_songs` | 全閾値到達の曲を3曲（129pt） | `points=129`（≥MAX_KEYS）、`overflow_color`あり、`overflow_upper_bound=MAX_POSSIBLE_KEY_COUNT` |

#### 20-4. `build_keyboard_geometry(key_count, black_key_color=None)`

key_countは白鍵の本数（度数）ではなく、黒鍵も含めた実際の鍵の総数として扱う（コードレビュー指摘対応: 以前はkey_count=白鍵の本数で、1増えても黒鍵は無視され白鍵だけが増えていた。ラ(A)から始まる12半音の繰り返し〔`CHROMATIC_IS_WHITE`〕をkey_count個分たどり、白鍵・黒鍵それぞれの本数と黒鍵の位置一覧を返す）。ラから始まるため、`MAX_KEYS`(88)に到達した状態は白鍵52本・黒鍵36本となり、現実の88鍵ピアノの内訳と一致する。`black_key_color`を指定すると全ての黒鍵をその色で塗る（鍵歴の上限超過表現用）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 鍵盤数0 | `key_count=0` | 白鍵0・黒鍵なし、`width=0` |
| 1鍵目は白鍵 | `key_count=1` | ラ(A)のため白鍵1本、黒鍵なし |
| 2鍵目は黒鍵が増える（回帰） | `key_count=2` | ラ#(A#)が加わり白鍵は1本のまま、黒鍵が1本増える |
| 1オクターブ分 | `key_count=12` | 白鍵7本・黒鍵5本（標準的なピアノの配列と一致） |
| 黒鍵の色指定 | `black_key_color`を指定 | 生成された黒鍵全てにその色が設定される |
| 白鍵で終わる場合の幅 | `key_count=8`（ミ/Eで終わる） | `width`は白鍵5本分のみ（黒鍵のはみ出し無し） |
| 黒鍵で終わる場合の幅 | `key_count=2`（ラ#/A#で終わる） | `width`は白鍵1本分+黒鍵のはみ出し分を含む |
| `white_keys`の反復可能性 | 任意の`key_count` | `white_key_count`個の要素を反復できる |

`AuthorStatsView`では、authorに曲が1件も無い場合（`get_view_like_pairs`の戻り値が空リスト）は鍵歴コンポーネント自体を非表示にする（`tests/test_views.py`の`test_kenreki_hidden_when_author_has_no_songs`）。

---

### 21. `lib/youtube.py` — YouTube Data API連携（#1146）

**テストファイル**: `tests/test_lib_youtube.py`

YouTube Data API（`build`）はモック化する。「動画が存在しない（削除・非公開）」場合と「APIの呼び出しに失敗した」場合を区別し、前者は`{}`を返し、後者は`YoutubeApiError`を送出する。クォータ超過（`quotaExceeded`・`dailyLimitExceeded`）・APIキーや設定の問題（未設定・`keyInvalid`・`keyExpired`・`accessNotConfigured`・`SERVICE_DISABLED`・`API_KEY_`から始まる理由）は以降の呼び出しも全て失敗し続けるため、`YoutubeApiError`のサブクラスである`YoutubeApiUnavailableError`を送出する。理由はエラーレスポンスの`errors`・`details`の両方から取得する。`rateLimitExceeded`は短時間で回復するため、`YoutubeApiUnavailableError`にはしない。元の例外の文字列にはAPIキーを含むURLが入るため、例外は連鎖させず（`from None`）、メッセージにはHTTPステータス・理由・元の例外のクラス名のみを入れる。

#### 21-1. `get_youtube_api(video_id)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 動画の情報を取得 | `items`に動画が1件 | `view`・`like`・`title`・`author`・`upload_time`（日本標準時）を返す |
| プレミア公開前の動画 | `liveBroadcastContent="upcoming"`・`scheduledPublishTime`あり | `upload_time`は`scheduledPublishTime`を日本標準時にした値 |
| 高評価数が非公開 | `statistics`に`likeCount`が無い | `like=0` |
| 動画が削除・非公開 | `items`が空 | `{}`を返す |
| クォータ超過 | `HttpError` 403・`reason`が`quotaExceeded`・`dailyLimitExceeded` | `YoutubeApiUnavailableError`を送出し、メッセージに「クォータを超過しました」と理由が含まれる |
| APIキーや設定の問題 | `HttpError` 400・`errors`の`reason`が`keyInvalid`・`keyExpired`、`HttpError` 400・`details`の`reason`が`API_KEY_INVALID`、`HttpError` 403・`details`の`reason`が`API_KEY_SERVICE_BLOCKED`、`HttpError` 403・`accessNotConfigured`／`SERVICE_DISABLED` | `YoutubeApiUnavailableError`を送出し、メッセージに「APIキーまたは設定に問題があります」が含まれる |
| レート制限 | `HttpError` 403・`reason="rateLimitExceeded"` | 短時間で回復するため`YoutubeApiError`を送出する（`YoutubeApiUnavailableError`ではない）。メッセージに理由が含まれる |
| その他の403 | `HttpError` 403・`reason="forbidden"` | `YoutubeApiError`を送出する（`YoutubeApiUnavailableError`ではない） |
| サーバーエラー | `HttpError` 500 | `YoutubeApiError`を送出する（`YoutubeApiUnavailableError`ではない） |
| 想定外の形式のエラーレスポンス | `HttpError` 403・`error`が文字列、`errors`が文字列、`reason`が文字列でない | `YoutubeApiError`以外の例外を送出せず、`YoutubeApiError`を送出する（`YoutubeApiUnavailableError`ではない） |
| JSONでないエラーレスポンス | `HttpError` 502・本文がHTML | `YoutubeApiError`を送出する（`YoutubeApiUnavailableError`ではない） |
| 通信エラー・タイムアウト | `socket.timeout` | `YoutubeApiError`を送出する（`YoutubeApiUnavailableError`ではない）。メッセージに元の例外のクラス名が含まれる |
| 想定外のレスポンス | `items`に動画はあるが`statistics`が無い | `YoutubeApiError`を送出する（動画は存在するため`{}`は返さない）。メッセージに元の例外のクラス名（`KeyError`）が含まれる |
| APIキーを漏らさない | `HttpError`のURLにAPIキーが含まれる（`quotaExceeded`・`keyInvalid`・`forbidden`） | 例外のメッセージにAPIキーが含まれない（Discordの公開チャンネルに通知されるため）。例外が連鎖していない（`__cause__`が`None`・`__suppress_context__`が`True`。トレースバックにAPIキーが出力されないため） |
| APIキー未設定 | `YOUTUBE_API_KEY=""` | `YoutubeApiUnavailableError`を送出し、APIは呼び出さない |

---

### 22. `lib/ogp.py` — ページごとのOGP画像（#1058）

**テストファイル**: `tests/test_lib_ogp.py`

各ページの`metatitle`を中央に、下線の下にロゴと「全て歌詞の所為です。」を置いた1200×630のPNGをPillowで生成する。フォントはサイトと同じ`GenZenGothicKaiC.woff2`。画像の見た目（中央寄せ・余白）はDjangoテストでは確認しきれないため、開発サーバーで`/ogp/<token>.png`を開いて目視で確認する。

#### 22-1. `make_ogp_token(title)` / `load_ogp_token(token)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 往復 | `全て歌詞の所為です。` | `load_ogp_token`で同じ文字列に戻る |
| 文字列以外は文字列にする | `__str__`が`全て12の所為です。`を返すオブジェクト（EditorViewは`metatitle`に`Editor`を渡す） | `全て12の所為です。`に戻る |
| タイトルを正規化する | `"曲名\n­ 作者"` | `曲名 作者`に戻り、`曲名\n作者`と`曲名 作者`のトークンが同じになる |
| 長いタイトルは切り詰める | `OGP_TITLE_MAX_LENGTH`+50文字 | `OGP_TITLE_MAX_LENGTH`文字に切り詰められる（URLの長さを抑えるため） |
| URLに使える文字のみ | `全て歌詞の所為です。 / 全てあなたの所為です。` | トークンが`[A-Za-z0-9_.:-]`のみ |
| 改ざんされたトークン | 末尾の1文字を変えたトークン | `BadSignature` |
| saltが異なるトークン | `signing.dumps("トップ", compress=True)` | `BadSignature` |

#### 22-2. `wrap_text(text, font, max_width)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 短い文字列は1行 | `トップ` | `["トップ"]` |
| 各行が最大幅に収まる | `あ`×40 | 複数行で、各行の幅が`max_width`以下、連結すると元の文字列 |
| 英単語は途中で折り返さない | `Quick Brown`（`max_width`は`Quick Bro`の幅） | `["Quick", "Brown"]` |
| 最大幅を超える英単語は文字単位で折り返す | `Supercalifragilistic`（`max_width`は`Supercali`の幅） | 複数行で、各行の幅が`max_width`以下、連結すると元の文字列 |
| 行頭禁則 | `あいうえお。かきくけこ、さしすせそ」たちつてと`（`max_width`を`あ`×3〜9の幅で変える） | どの行も`、`・`。`・`」`で始まらない |
| 行の後半の空白で折り返す | `全て歌詞の所為です。 / 全てあなたの所為です。` | `["全て歌詞の所為です。 /", "全てあなたの所為です。"]` |
| 行の前半の空白では折り返さない | `"A " + "あ" * 30` | 1行目が`A あ`で始まる |

#### 22-3. `layout_title(title)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 短いタイトルは最大のフォントサイズ | `トップ` | フォントサイズが`TITLE_FONT_SIZES[0]`、`["トップ"]` |
| 行数・高さ・幅が上限以内 | 英語の長いタイトル、`あ`×60 | 行数が`TITLE_MAX_LINES`以下、高さが`TITLE_MAX_HEIGHT`以下、各行の幅が`TITLE_MAX_WIDTH`以下 |
| 収まらないタイトルは三点リーダーで省略 | `あ`×`OGP_TITLE_MAX_LENGTH` | 最小のフォントサイズで`TITLE_MAX_LINES`行、最終行が`…`で終わり幅が`TITLE_MAX_WIDTH`以下 |

#### 22-4. `render_ogp_image(title)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 1200×630のPNG | `トップ` | PNGで、サイズが1200×630 |
| タイトルごとに異なる画像 | `トップ`と`統計` | 異なるバイト列 |
| タイトルとロゴが重ならない | 英語の長いタイトル、`あ`×`OGP_TITLE_MAX_LENGTH` | y=480〜520の帯がすべて背景色（タイトル・下線とロゴの間に何も描かれない） |
| 描画はロックの中で行う | `RENDER_LOCK`をモック | `__enter__`・`__exit__`が1回ずつ呼ばれる（FreeTypeのフォントを複数のスレッドから同時に使わないため。runserverはスレッドで動く） |
| 複数のスレッドから同時に生成しても同じ画像 | 同じタイトルを4スレッドで8回生成 | すべて1スレッドで生成した画像と同じバイト列 |
| 描画の前にタイトルを正規化する | `"曲名\n­作者"`と`曲名 作者` | 同じバイト列（改行をそのまま描くと複数行のテキストとして扱われ、位置がずれるため） |

#### 22-5. `normalize_title(title)`

改行や連続した空白を1つの空白にまとめ、ソフトハイフン・ゼロ幅スペースなどの見えない文字（Unicodeの書式文字`Cf`）を取り除く。見えない文字はブラウザでは表示されないが、フォントによっては画像に記号として描かれる（開発用DBに、曲名がソフトハイフンと空白の繰り返しの曲がある）。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 空白・改行をまとめる | `" 曲名\n\t作者  名　前 "` | `曲名 作者 名 前` |
| 見えない文字を取り除く | `"曲­名​‌"` | `曲名` |
| 見えない文字だけなら空 | `"­ ­ ​"` | `""` |
| 文字列以外は文字列にする | `__str__`が`全て12の所為です。`を返すオブジェクト | `全て12の所為です。` |

#### 22-6. `get_font(size)`

フォントに無い文字は`.notdef`のグリフで描かれる（Pillowは他のフォントで代替しない。ブラウザでも、どのフォントにも無い文字は最初のフォントの`.notdef`で描かれる）。`GenZenGothicKaiC.woff2`の`.notdef`が「ぎ」の形だったため、中抜きの四角（豆腐）に差し替えた（#212）。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| フォントに無い文字は豆腐で描く | `한`・`🎵`・`U+E000`（私用領域）・`U+0378`（未割り当て）を`TITLE_FONT_SIZES[0]`で描き、描かれた範囲で切り抜く | 中央の画素が描かれず、上下左右の辺の中点が描かれる（中抜きの四角） |

---

### 23. `templatetags/ogp.py` — OGP画像のURL（#1058）

**テストファイル**: `tests/test_templatetags_ogp.py`

#### 23-1. `get_ogp_image_url(metatitle)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| metatitleから画像のURLを作る | `トップ` | `{ROOT_URL}/ogp/<token>.png?v={OGP_VERSION}`で、`token`を復元すると`トップ` |
| metatitleを正規化する | `"  トップ　"`・`"曲名\n­作者"` | `token`を復元すると、それぞれ`トップ`・`曲名 作者` |
| metatitleが無い・空白や見えない文字のみ | `None`・`""`・`" "`・全角空白と改行・ソフトハイフンとゼロ幅スペース | 共通の画像`{ROOT_URL}/static/subekashi/image/ogp.png` |
| `ROOT_URL`の設定を使う | `override_settings(ROOT_URL="https://example.com")` | 画像のURLが`https://example.com/ogp/`・`https://example.com/static/...`から始まる（`config.settings`ではなく`django.conf.settings`から読むため、テストで差し替えられる） |

---

### 24. `lib/ip.py` — クライアントのIP（#1188）

**テストファイル**: `tests/test_lib_ip.py`

#### 24-1. `get_client_ip(request)`

`django_ratelimit`の`key='ip'`で使うIP（`settings.RATELIMIT_IP_META_KEY`）。PythonAnywhereでは`REMOTE_ADDR`がロードバランサーのIPになるため、ロードバランサーが付ける`X-Real-IP`を使う。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| X-Real-IPを使う | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP: 203.0.113.1` | `203.0.113.1` |
| X-Real-IPが無い | `REMOTE_ADDR: 10.0.0.1` のみ | `10.0.0.1` |
| X-Real-IPが空 | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP: ""` | `10.0.0.1` |
| X-Real-IPがIPでない | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP`が`not-an-ip`・`203.0.113.1, 198.51.100.1`・`203.0.113.1/24` | `10.0.0.1`（`django_ratelimit`がIPとして解析できず500になるため） |
| IPv6のX-Real-IP | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP: 2001:db8::1` | `2001:db8::1` |
| REMOTE_ADDRも無い | `REMOTE_ADDR`・`X-Real-IP`なし | `KeyError`（`django_ratelimit`の既定と同じく`request.META['REMOTE_ADDR']`を読み、`None`を返さない） |
| X-Forwarded-Forは使わない | `REMOTE_ADDR: 10.0.0.1`、`X-Forwarded-For: 198.51.100.1` | `10.0.0.1`（クライアントが自由に付けられるため） |

---

## テスト優先度

| 優先度 | 対象 | 理由 |
| --- | --- | --- |
| **高** | `lib/url.py` | ビジネスロジックの核心、URLの正規化は多くの機能に影響 |
| **高** | `lib/song_service.py` | 曲作成・更新・削除という中核機能 |
| **高** | `forms.py` | バリデーションの正確性はユーザー入力の安全性に直結 |
| **高** | `lib/query_utils.py` | 単純な関数で副作用がなく、テストしやすく確実に動作すべき |
| **中** | `lib/query_filters.py` | 検索機能のコア、DB依存テスト |
| **中** | `lib/song_search.py` | ページネーションロジックのエッジケース |
| **中** | ビュー (`test_views.py`) | HTTP レスポンスの基本確認 |
| **中** | REST API (`test_api.py`) | APIレスポンス形式の確認 |
| **低** | `lib/author_helpers.py` | `test_author_migration.py` に既に類似テストあり |
| **低** | ミドルウェア | 結合テストに近く、設定依存 |
| **低** | `article` アプリ | 機能がシンプルで変更頻度が低い |

---

## テスト実装の方針

1. **テストフレームワーク**: Django標準の `TestCase` を使用
2. **DBテスト**: `TestCase` がトランザクションを自動ロールバックするため、各テストは独立
3. **外部API依存の排除**: Discord通知・外部URLアクセスは `unittest.mock.patch` でモック化
4. **純粋関数のテスト**: `lib/url.py`, `lib/query_utils.py` など副作用のない関数は `SimpleTestCase` で十分
5. **テストデータ**: `setUp` メソッドでモデルオブジェクトを直接作成（fixtureは使わない）

---

## ファイル構成

```
subekashi/tests/
├── __init__.py
├── TEST_PLAN_UNIT.md               # このファイル
├── test_author_migration.py        # 既存
├── song.py                         # 既存（外部依存あり）
├── test_lib_url.py                 # 実装済み: URL処理ユーティリティ
├── test_lib_song_service.py        # 実装済み: 曲サービス
├── test_lib_query_filters.py       # 実装済み: クエリフィルター
├── test_lib_query_utils.py         # 実装済み: クエリユーティリティ
├── test_lib_author_helpers.py      # 実装済み: 作者ヘルパー
├── test_lib_song_search.py         # 実装済み: 検索機能
├── test_forms.py                   # 実装済み: フォームバリデーション
├── test_views.py                   # 実装済み: ビュー（GET・POST）
├── test_api.py                     # 実装済み: REST API
├── test_middleware.py              # 実装済み: ミドルウェア
├── test_security.py                # 実装済み: CSP・CORS・CSRFトークン・SRI（結合、#1126）
├── test_models.py                  # 実装済み: モデル基本動作
├── test_converters.py              # 実装済み: URLコンバータ
├── test_lib_youtube.py             # 実装済み: YouTube Data API連携
├── test_lib_ogp.py                 # 実装済み: ページごとのOGP画像
├── test_lib_ip.py                  # 実装済み: クライアントのIP
├── test_management_commands.py     # 実装済み: 管理コマンド
├── test_templatetags_song_card.py  # 実装済み: song_card テンプレートタグ
└── test_templatetags_ogp.py        # 実装済み: ogp テンプレートタグ

article/
└── tests.py                        # 実装済み: ArticlesView・DefaultArticleView
```

## 今後の課題

- **`SongEditView` POST テスト** (`test_views.py` への追加)
  - 正常時のリダイレクト先・バリデーションエラー時の再表示（YouTube API 呼び出しのモック化が必要）
