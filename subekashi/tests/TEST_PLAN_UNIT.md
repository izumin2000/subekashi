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

#### 3-1-2. `filter_by_guesser(guesser)`（別名・双方向対応の追加分）

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 別名（正方向・逆方向）一致 | `filter_by_keyword`と同様の`yamada`/`sasaki`構成 | 正方向・逆方向いずれの検索語でも双方の曲が結果に含まれる |

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

#### 3-4. `make_is_lack_annotation()`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 未完成の曲に annotate | 上記の `filter_by_lack` と同じ条件 | `is_lack=True` がアノテートされる |
| 完成した曲に annotate | URLと歌詞が揃っている曲 | `is_lack=False` がアノテートされる |
| `is_subeana=True` かつ特殊作者(id=1)なしの曲に annotate | `is_original=False`, `is_subeana=True`, `imitates`なし, 特殊作者(id=1)の紐付けなし | `is_lack=True` がアノテートされる |
| 特殊作者(id=1)が紐づいている曲に annotate | 上記に加え特殊作者(id=1)を紐付け | `is_lack=False` がアノテートされる |
| `is_questionable=True` かつURLなし・削除されていない曲に annotate | `is_questionable=True`, SongLink なし | `is_lack=True` がアノテートされる（URLなし条件は `is_questionable` を問わない） |
| `is_questionable=True` かつ歌詞なし等の曲に annotate | `is_questionable=True`, URLあり、歌詞なし等 | `is_lack=False` がアノテートされる（歌詞なし条件は `is_questionable=False` が必須） |

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

---

### 5. `lib/author_helpers.py` — 作者ヘルパー

**テストファイル案**: `tests/test_lib_author_helpers.py` （既存の `test_author_migration.py` に追加可能）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 新規作者の一括作成 | `["新作者A", "新作者B"]` | 2つのAuthorが作成されDBに保存 |
| 既存作者は新規作成しない | DBに存在する作者名 | 同じAuthorオブジェクトが返される（重複なし）|
| 空文字列をスキップ | `["作者A", "", "作者B"]` | 空文字列を除いた2件のAuthor |
| 全て空文字列 | `["", ""]` | 空のリスト |

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

---

### 7. ビュー — ページアクセスと HTTP レスポンス

**テストファイル案**: `tests/test_views.py`

#### 7-1. `TopView` (`/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| テンプレートが使用される | GETリクエスト | `subekashi/top.html` がレンダリングされる |

#### 7-2. `SongsView` (`/songs/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| キーワード検索 | `?keyword=テスト` | HTTP 200、結果が絞られる |
| ページネーション | `?page=2&size=10` | HTTP 200 |
| 不正なページ番号 | `?page=abc` | HTTP 200 (デフォルト page=1 で処理) |
| 真偽値クエリ (大文字True) | `?is_draft=True` | context["is_draft"] = True (チェックボックス有効) |
| 真偽値クエリ (数値1) | `?is_draft=1` | context["is_draft"] = True |
| 真偽値クエリ (大文字False) | `?is_draft=False` | context["is_draft"] = False |
| is_joke=True | `?is_joke=True` | context["jokerange"] = "only" |
| is_joke=only | `?is_joke=only` | context["jokerange"] = "only" |
| is_joke=False | `?is_joke=False` | context["jokerange"] = "off" |
| is_joke=off | `?is_joke=off` | context["jokerange"] = "off" |
| is_joke=all | `?is_joke=all` | context["jokerange"] = "on" |
| is_joke=on | `?is_joke=on` | context["jokerange"] = "on" |
| is_original/is_inst 大文字True | `?is_original=True` など | 対応 context フィールドが True |
| is_questionable 大文字True | `?is_questionable=True` | context["is_questionable"] = True |

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
| POST: 作者が空白 | `url=""`, `authors="  "` | HTTP 200、"作者" を含むエラー |
| POST: タイトルが空 | `url=""`, `authors="テスト作者"`, `title=""` | HTTP 200、"タイトル" を含むエラー |
| POST: is-questionable時、オリジナル模倣は強制OFF・その他フラグの入力値はそのまま保存される | `is-questionable-manual=on`, `is-original-manual=on`, `is-subeana-manual=on` | 保存されたSongの `is_questionable=True`、`is_original=False`、`is_subeana=True` |

#### 7-5. `SongEditView` (`/songs/<id>/edit/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲のGET | 有効なsong_id | HTTP 200 |
| 存在しない曲のGET | 無効なsong_id | HTTP 404 |
| POST: is_questionable時に歌詞・模倣・下書き・オリジナル模倣が強制的に空/OFF | `is_questionable=True`, `lyrics="..."`, `imitate="<id>"`, `is_draft=True`, `is_original=True` | 保存されたSongの `lyrics=""`、`imitates`が空、`is_draft=False`、`is_original=False`、`is_questionable=True` |
| POST: is_questionable時も非公開/削除済み・ネタ曲・インスト・すべあな界隈曲は保存される | `is_questionable=True`, `is_deleted=True`, `is_joke=True`, `is_inst=True`, `is_subeana=True` | 各フラグがそれぞれ `True` のまま保存される |

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

#### 7-8-1. `AuthorAliasesView` (`/authors/<id>/aliases`)（#992）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 別名なし | 別名未登録のauthor | HTTP 200、「別名が見つかりませんでした」 |
| 正方向の別名 | 別名を1件登録 | 別名名が表示され、編集・削除リンクが含まれる |
| 逆方向の別名 | 他authorが自分のnameと一致する別名を保持 | 相手authorの名前が表示されるが、編集・削除リンクは含まれない |
| `alias_type=past`かつ対象authorが実在 | 別名nameと同名のAuthorが存在 | `channel/<name>/`へのリンクが含まれる |
| `alias_type=past`だが対象authorが不在 | 別名nameと同名のAuthorが存在しない | `channel/<name>/`へのリンクが含まれない |
| `alias_type`がpast/another以外 | 例: `abbr`。対象authorは実在 | `channel/<name>/`へのリンクが含まれない |

#### 7-8-2. `AuthorAliasNewView` (`/authors/<id>/aliases/new`)（#992）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 正常なPOST | 有効な`name`・`alias_type` | AuthorAliasが作成され一覧画面へリダイレクト |
| 正常なPOST | 上記 | `History.create_for_author()`が呼ばれ、`history_type="new"`のレコードが作成される |
| nameが重複 | 既存のname | HTTP 200のままエラー表示、レコードは作成されない |
| nameがauthor自身と同じ | `name=author.name` | HTTP 200のままエラー表示、レコードは作成されない |

#### 7-8-3. `AuthorAliasEditView` (`/authors/<id>/aliases/<alias_id>/edit`)（#992）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| 存在しないalias_id | 無効なalias_id | HTTP 404 |
| 他authorが所有するalias_id | 別authorのalias_idを指定 | HTTP 404 |
| 正常なPOST | 有効な`name`・`alias_type` | AuthorAliasが更新され一覧画面へリダイレクト |
| 正常なPOST | 上記 | `History.create_for_author()`が呼ばれ、`history_type="edit"`のレコードが作成される |
| 自分自身の現在のnameのまま更新 | `name`を変更しない | 重複エラーにならず更新される |
| 他のaliasのnameと重複 | 同一author内の他のalias.name | HTTP 200のままエラー表示、更新されない |

#### 7-8-4. `AuthorAliasDeleteView` (`/authors/<id>/aliases/<alias_id>/delete`)（#992）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200、削除確認内容が表示される |
| 存在しないalias_id | 無効なalias_id | HTTP 404 |
| 正常なPOST | POSTリクエスト | AuthorAliasが削除され一覧画面へリダイレクト |
| 正常なPOST | 上記 | `History.create_for_author()`が呼ばれ、`history_type="delete"`、`history.author`は削除後も維持される |

#### 7-9. `ChannelView` (`/channel/<name>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する作者名 | 有効なchannel_name | `/authors/<id>/` へリダイレクト (HTTP 302) |
| 存在しない作者名 | 無効なchannel_name | HTTP 404 |

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

---

### 8. REST API ビュー

**テストファイル案**: `tests/test_api.py`

#### 8-1. `SongAPI` (`/api/song/`)

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| パラメータなし | GETリクエスト | HTTP 200、JSON形式の曲一覧 |
| キーワード検索 | `?keyword=テスト` | HTTP 200、絞り込み結果 |
| ページネーション | `?page=1&size=5` | HTTP 200、最大5件 |
| 不正なsize | `?size=-1` | HTTP 200、デフォルトサイズで処理 |
| 統計情報の含有 | GETリクエスト | レスポンスに `count`, `page`, `max_page` が含まれる |

#### 8-2. `EditorIsOpenView` (`/api/editor/is_open`)

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200、`is_open` フィールドを含むJSON |

---

### 9. ミドルウェア

**テストファイル案**: `tests/test_middleware.py`

#### 9-1. `RatelimitMiddleware`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 通常リクエスト | Ratelimited例外なし | 通常のレスポンスを返す |
| レート制限を超えた場合 | Ratelimited例外が発生 | HTTP 429、`{"error": "Rate limit exceeded"}` |

#### 9-2. `CacheControlMiddleware`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 静的ファイルURL | `/static/` へのリクエスト | Cache-Controlヘッダーが設定される |
| 通常ページURL | `/` へのリクエスト | Cache-Controlが適切に設定される |

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

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| 作者の作成 | `Author.objects.create(name="テスト作者")` | DBに保存される |
| `name` のユニーク制約 | 同じ名前で2件作成 | `IntegrityError` が発生 |

#### 11-3. `AuthorAlias` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| エイリアスの作成 | `AuthorAlias.objects.create(name="別名", author=author)` | DBに保存される |
| `name` のユニーク制約 | 同じ名前で2件作成 | `IntegrityError` が発生 |
| `alias_type` のデフォルト値 | `alias_type` 未指定で作成 | `alias_type == "another"` |

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

#### 11-4. `SongLink` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| リンクの作成 | `SongLink.objects.create(url="https://youtu.be/xxx")` | DBに保存される |
| `url` のユニーク制約 | 同じURLで2件作成 | `IntegrityError` が発生 |
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

#### 12-2. `DefaultArticleView` (`/articles/<id>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する公開記事ID | 有効なarticle_id、`is_open=True` | HTTP 200 |
| 記事タイトルの表示 | 有効なarticle_id | レスポンスにタイトルが含まれる |
| 存在しない記事ID | 無効なarticle_id | HTTP 404 |
| 非公開記事 | `is_open=False` | HTTP 404 |

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

DBロックエラー対策で全件処理時に先にID一覧を取得する方式に変更したことに対応（YouTube APIはモック化）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| `-id` 指定 | 特定のSongのみ対象 | 指定Songのみ`view`等が更新される |
| `-id` 未指定 | SongLinkが紐づく全Song | 該当する全Songが更新される |
| SongLinkが無いSong | 対象外 | 更新されない（スキップ） |
| 全動画が取得不可 | `get_youtube_api` が `{}` を返す | `is_deleted=True` で保存される |

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
├── test_models.py                  # 実装済み: モデル基本動作
├── test_converters.py              # 実装済み: URLコンバータ
├── test_management_commands.py     # 実装済み: 管理コマンド
└── test_templatetags_song_card.py  # 実装済み: song_card テンプレートタグ

article/
└── tests.py                        # 実装済み: ArticlesView・DefaultArticleView
```

## 今後の課題

- **`SongEditView` POST テスト** (`test_views.py` への追加)
  - 正常時のリダイレクト先・バリデーションエラー時の再表示（YouTube API 呼び出しのモック化が必要）
