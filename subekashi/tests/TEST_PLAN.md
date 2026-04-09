# テスト計画書

作成日: 2026-04-07

## 概要

このドキュメントは `subekashi` プロジェクト全体のテスト計画をまとめたものです。
現状、`test_author_migration.py` にAuthor関連の基本テストが存在しますが、全体的なカバレッジは低い状態です。

---

## 既存テスト

| ファイル | テストクラス | 状態 |
|---|---|---|
| `tests/test_author_migration.py` | AuthorModelTest, SongAuthorRelationshipTest, AuthorHelpersTest, AuthorViewTest, ChannelRedirectTest, SongDisplayTest | 作成済み |
| `tests/song.py` | SongPageTest | 外部API依存（結合テスト）|

---

## テスト計画一覧

---

### 1. `lib/url.py` — URL処理ユーティリティ

**テストファイル案**: `tests/test_lib_url.py`

#### 1-1. `is_youtube_url(url)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 通常のYouTube URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `True` |
| YouTubeショートURL | `https://youtube.com/shorts/abcdefghijk` | `True` |
| 短縮YouTube URL (youtu.be) | `https://youtu.be/dQw4w9WgXcQ` | `True` |
| モバイル版YouTube URL | `https://m.youtube.com/watch?v=dQw4w9WgXcQ` | `True` |
| 非YouTube URL | `https://nicovideo.jp/watch/sm12345` | `False` |
| 空文字列 | `""` | `False` |

#### 1-2. `get_youtube_id(url)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 通常URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| youtu.be URL | `https://youtu.be/dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| ショートURL | `https://youtube.com/shorts/abcdefghijk` | `"abcdefghijk"` |
| 非YouTube URL | `https://example.com` | `"https://example.com"` (そのまま返す) |

#### 1-3. `format_youtube_url(url)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 通常YouTube URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"https://youtu.be/dQw4w9WgXcQ"` |
| 既に短縮済み | `https://youtu.be/dQw4w9WgXcQ` | `"https://youtu.be/dQw4w9WgXcQ"` |
| 非YouTube URL | `https://nicovideo.jp/watch/sm12345` | `"https://nicovideo.jp/watch/sm12345"` (変化なし) |

#### 1-4. `format_x_url(url)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| Twitter URL (クエリあり) | `https://twitter.com/user/status/123?s=20` | `"https://x.com/user/status/123"` |
| x.com URL | `https://x.com/user/status/123` | `"https://x.com/user/status/123"` |
| 非X URL | `https://example.com/path?q=1` | そのまま返す |

#### 1-5. `clean_url(urls)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| スペース付きカンマ区切り | `"url1, url2"` | `"url1,url2"` |
| www付きURL | `"https://www.youtube.com/watch?v=abc1234abcd"` | `"https://youtu.be/abc1234abcd"` |
| Googleリダイレクトリンク | `"https://www.google.com/url?q=https://youtu.be/abc1234abcd"` | `"https://youtu.be/abc1234abcd"` |
| 複数URL | `"https://youtu.be/abc1234abcd,https://x.com/u/1"` | 各URLが正規化されたカンマ区切り |

---

### 2. `lib/song_service.py` — 曲サービス

**テストファイル案**: `tests/test_lib_song_service.py`

#### 2-1. `check_reject_list(authors)`

| テストケース | 前提条件 | 期待結果 |
|---|---|---|
| NGリストに含まれる作者 | `REJECT_LIST = ["NGアーティスト"]`、該当Authorオブジェクト | エラーメッセージ文字列を返す |
| NGリストに含まれない作者 | 通常のAuthorオブジェクト | `None` を返す |
| REJECT_LISTがインポートできない場合 | ImportError発生 | `None` を返す (空リスト扱い) |
| 空のauthorsリスト | `[]` | `None` を返す |

#### 2-2. `validate_song_url(cleaned_url, exclude_song_id=None)`

| テストケース | 前提条件 | 期待結果 |
|---|---|---|
| 既存URLと重複する | SongLinkが既に存在し曲に紐付いている | エラーメッセージ文字列を返す |
| 重複しないURL | 新しいURL | `None` を返す |
| 自分自身を除外した場合 | `exclude_song_id` を指定し、同じ曲のURL | `None` を返す |
| `allow_dup=True` のSongLink | 重複URLだが `allow_dup=True` | `None` を返す |
| 曲に紐付いていないSongLink | リンクは存在するが曲なし | `None` を返す |

#### 2-3. `create_song(fields)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 正常な曲作成 | 有効な `SongFields` | Songオブジェクトが保存される |
| `post_time` が自動設定される | fields に `post_time` なし | `timezone.now()` に近い時刻が設定される |
| 各フラグが正しく設定される | `is_original=True`, `is_joke=False` など | Song属性がfieldsと一致する |

#### 2-4. `get_imitate_songs(imitates_str, self_id)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| カンマ区切りのID | `"1,2,3"`, `self_id=0` | 存在するSongのリスト |
| 自分自身のIDを含む | `"1,2"`, `self_id=1` | IDが1の曲は除外される |
| 数値以外の文字列を含む | `"1,abc,2"` | 数値のみ処理、例外なし |
| 空文字列 | `""` | 空のリスト |
| スペースを含む | `" 1 , 2 "` | 正常に処理される |

#### 2-5. `update_song(song, fields, author_objects, imitate_songs, cleaned_url_list)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 既存URLの削除 | 新しいURLリストに含まれないURL | `SongLink.songs` から削除される |
| 他の曲に紐付かないURLは完全削除 | URLが他の曲にない | SongLinkレコードごと削除される |
| 新しいURLの追加 | 新しいURL | SongLinkが作成・紐付けられる |
| 作者の更新 | 新しい author_objects | Song.authors が更新される |
| トランザクション失敗時のロールバック | DB エラーを模擬 | 変更が元に戻る |

#### 2-6. `build_delete_discord_text(song, reason, editor)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 正常なテキスト生成 | 曲オブジェクト、理由、編集者 | 曲ID・タイトル・作者・理由を含む文字列 |

#### 2-7. `build_edit_song_discord_text(song_id, song, fields, author_objects, cleaned_url, imitate_songs)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| タイトル変更 | before と after が異なるタイトル | 変更差分が `changes` リストに含まれる |
| 変更なし | before と after が同じ | `changed_labels` が空リスト |
| 複数フィールドの変更 | 複数の差分 | 全変更が `changes` に含まれ、`edit_title` に反映 |

---

### 3. `lib/query_filters.py` — クエリフィルター

**テストファイル案**: `tests/test_lib_query_filters.py`

#### 3-1. `filter_by_keyword(keyword)`

| テストケース | 前提条件 | 期待結果 |
|---|---|---|
| タイトル部分一致 | キーワードがタイトルに含まれる曲 | その曲が結果に含まれる |
| 作者名部分一致 | キーワードが作者名に含まれる | その曲が結果に含まれる |
| 歌詞部分一致 | キーワードが歌詞に含まれる | その曲が結果に含まれる |
| URL部分一致 | キーワードがURLに含まれる | その曲が結果に含まれる |
| 一致なし | 存在しないキーワード | 空のクエリセット |

#### 3-2. `filter_by_lack()`

| テストケース | 前提条件 | 期待結果 |
|---|---|---|
| URLなし・削除されていない曲 | `is_deleted=False`, SongLink なし | 結果に含まれる |
| 歌詞なし・インストではない曲 | `is_inst=False`, `lyrics=""` | 結果に含まれる |
| すべて完備している曲 | URL・歌詞・作者あり | 結果に含まれない |

#### 3-3. `make_is_lack_annotation()`

| テストケース | 前提条件 | 期待結果 |
|---|---|---|
| 未完成の曲に annotate | 上記の `filter_by_lack` と同じ条件 | `is_lack=True` がアノテートされる |
| 完成した曲に annotate | URLと歌詞が揃っている曲 | `is_lack=False` がアノテートされる |

---

### 4. `lib/query_utils.py` — クエリユーティリティ

**テストファイル案**: `tests/test_lib_query_utils.py`

#### 4-1. `clean_query_params(query_params)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 通常の辞書 | `{"key": "value"}` | `{"key": "value"}` |
| リスト形式の値 | `{"key": ["first", "second"]}` | `{"key": "first"}` |
| 空のリスト | `{"key": []}` | `{"key": []}` (変化なし) |
| 混合 | `{"a": "val", "b": ["x", "y"]}` | `{"a": "val", "b": "x"}` |

#### 4-2. `has_view_filter_or_sort(query_data)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| `view_lte` が存在する | `{"view_lte": "100"}` | `True` |
| `sort=view` | `{"sort": "view"}` | `True` |
| `sort=-view` | `{"sort": "-view"}` | `True` |
| 関係ないキー | `{"sort": "title"}` | `False` |
| 空辞書 | `{}` | `False` |

#### 4-3. `has_like_filter_or_sort(query_data)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| `like_lte` が存在する | `{"like_lte": "50"}` | `True` |
| `sort=like` | `{"sort": "like"}` | `True` |
| `sort=-like` | `{"sort": "-like"}` | `True` |
| 空辞書 | `{}` | `False` |

---

### 5. `lib/author_helpers.py` — 作者ヘルパー

**テストファイル案**: `tests/test_lib_author_helpers.py` （既存の `test_author_migration.py` に追加可能）

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 新規作者の一括作成 | `["新作者A", "新作者B"]` | 2つのAuthorが作成されDBに保存 |
| 既存作者は新規作成しない | DBに存在する作者名 | 同じAuthorオブジェクトが返される（重複なし）|
| 空文字列をスキップ | `["作者A", "", "作者B"]` | 空文字列を除いた2件のAuthor |
| 全て空文字列 | `["", ""]` | 空のリスト |

---

### 6. `forms.py` — フォームバリデーション

**テストファイル案**: `tests/test_forms.py`

#### 6-1. `ContactForm`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 正常な入力 | `category="不具合の報告"`, `detail="詳細内容"` | `is_valid() == True` |
| categoryが空 | `category=""`, `detail="内容"` | `is_valid() == False`、エラーメッセージあり |
| detailが空 | `category="質問"`, `detail=""` | `is_valid() == False`、エラーメッセージあり |
| 不正なcategory値 | `category="不正な選択肢"` | `is_valid() == False` |

#### 6-2. `SongDeleteForm`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 正常な入力 | `reason="削除理由の詳細"` | `is_valid() == True` |
| reasonが空 | `reason=""` | `is_valid() == False`、`"削除理由を入力してください。"` |

#### 6-3. `SongEditForm`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 最低限の必須フィールドのみ | `title="タイトル"`, `authors="作者名"` | `is_valid() == True` |
| titleが空 | `title=""`, `authors="作者名"` | `is_valid() == False`、`"タイトルが未入力です。"` |
| authorsが空 | `title="タイトル"`, `authors=""` | `is_valid() == False`、`"作者は空白にできません。"` |
| urlは任意 | `url=""` (省略) | `is_valid() == True` |
| is_original など boolean フラグ | `is_original=True` | `cleaned_data["is_original"] == True` |
| titleが500文字超 | `title="あ" * 501` | `is_valid() == False` |

---

### 7. ビュー — ページアクセスと HTTP レスポンス

**テストファイル案**: `tests/test_views.py`

#### 7-1. `TopView` (`/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 正常アクセス | GETリクエスト | HTTP 200 |
| テンプレートが使用される | GETリクエスト | `subekashi/top.html` がレンダリングされる |

#### 7-2. `SongsView` (`/songs/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 正常アクセス | GETリクエスト | HTTP 200 |
| キーワード検索 | `?keyword=テスト` | HTTP 200、結果が絞られる |
| ページネーション | `?page=2&size=10` | HTTP 200 |
| 不正なページ番号 | `?page=abc` | HTTP 200 (デフォルト page=1 で処理) |

#### 7-3. `SongView` (`/songs/<id>/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 存在する曲ID | 有効なsong_id | HTTP 200 |
| 存在しない曲ID | 無効なsong_id | HTTP 404 |
| 削除済み曲 | `is_deleted=True` の曲 | HTTP 404 または特定の表示 |

#### 7-4. `SongNewView` (`/songs/new/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| GETアクセス | GETリクエスト | HTTP 200、フォームが表示される |

#### 7-5. `SongEditView` (`/songs/<id>/edit/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 存在する曲のGET | 有効なsong_id | HTTP 200 |
| 存在しない曲のGET | 無効なsong_id | HTTP 404 |

#### 7-6. `ContactView` (`/contact/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| GETアクセス | GETリクエスト | HTTP 200 |

#### 7-7. `AuthorView` (`/authors/<id>/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 存在する作者ID | 有効なauthor_id | HTTP 200 |
| 存在しない作者ID | 無効なauthor_id | HTTP 404 |

#### 7-8. `ChannelView` (`/channel/<name>/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 存在する作者名 | 有効なchannel_name | `/authors/<id>/` へリダイレクト (HTTP 302) |
| 存在しない作者名 | 無効なchannel_name | HTTP 404 |

#### 7-9. `HistoriesView` (`/histories/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 正常アクセス | GETリクエスト | HTTP 200 |

---

### 8. REST API ビュー

**テストファイル案**: `tests/test_api.py`

#### 8-1. `SongAPI` (`/api/song/`)

| テストケース | 入力 | 期待結果 |
|---|---|---|
| パラメータなし | GETリクエスト | HTTP 200、JSON形式の曲一覧 |
| キーワード検索 | `?keyword=テスト` | HTTP 200、絞り込み結果 |
| ページネーション | `?page=1&size=5` | HTTP 200、最大5件 |
| 不正なsize | `?size=-1` | HTTP 200、デフォルトサイズで処理 |
| 統計情報の含有 | GETリクエスト | レスポンスに `count`, `page`, `max_page` が含まれる |

#### 8-2. `EditorIsOpenView` (`/api/editor/is_open`)

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 正常アクセス | GETリクエスト | HTTP 200、`is_open` フィールドを含むJSON |

---

### 9. ミドルウェア

**テストファイル案**: `tests/test_middleware.py`

#### 9-1. `RatelimitMiddleware`

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 通常リクエスト | Ratelimited例外なし | 通常のレスポンスを返す |
| レート制限を超えた場合 | Ratelimited例外が発生 | HTTP 429、`{"error": "Rate limit exceeded"}` |

#### 9-2. `CacheControlMiddleware`

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 静的ファイルURL | `/static/` へのリクエスト | Cache-Controlヘッダーが設定される |
| 通常ページURL | `/` へのリクエスト | Cache-Controlが適切に設定される |

---

### 10. `lib/song_search.py` — 検索機能

**テストファイル案**: `tests/test_lib_song_search.py`

#### 10-1. `song_search(querys)`

| テストケース | 入力 | 期待結果 |
|---|---|---|
| 空のクエリ | `{}` | 全曲を返す、statisticsに`count`, `page`, `max_page`が含まれる |
| page=1, size=10 | `{"page": "1", "size": "10"}` | 最大10件の曲 |
| 不正なpage | `{"page": "abc"}` | デフォルト`page=1`で処理 |
| 不正なsize | `{"size": "0"}` | デフォルトsize(50)で処理 |
| `size` による `max_page` の計算 | 曲100件, `size=10` | `max_page=10` |
| バリデーションエラーのあるパラメータ | 不正なfiltersetパラメータ | `ValidationError` が発生 |

---

### 11. モデル — 基本動作

**テストファイル案**: `tests/test_models.py`

#### 11-1. `Song` モデル

| テストケース | 操作 | 期待結果 |
|---|---|---|
| 曲の作成 | `Song.objects.create(title="テスト曲", ...)` | DBに保存される |
| `authors_str()` メソッド | 複数作者を持つ曲 | 作者名がカンマ区切りで返される |
| `is_deleted=True` の曲 | 削除フラグを立てる | DBに残るが削除済みとして扱われる |
| ManyToMany: authors | `song.authors.add(author)` | 作者が曲に紐付く |
| ManyToMany: imitates (自己参照) | `song.imitates.add(other_song)` | 模倣関係が成立する |

#### 11-2. `Author` モデル

| テストケース | 操作 | 期待結果 |
|---|---|---|
| 作者の作成 | `Author.objects.create(name="テスト作者")` | DBに保存される |
| `name` のユニーク制約 | 同じ名前で2件作成 | `IntegrityError` が発生 |

#### 11-3. `AuthorAlias` モデル

| テストケース | 操作 | 期待結果 |
|---|---|---|
| エイリアスの作成 | `AuthorAlias.objects.create(name="別名", author=author)` | DBに保存される |
| `name` のユニーク制約 | 同じ名前で2件作成 | `IntegrityError` が発生 |

#### 11-4. `SongLink` モデル

| テストケース | 操作 | 期待結果 |
|---|---|---|
| リンクの作成 | `SongLink.objects.create(url="https://youtu.be/xxx")` | DBに保存される |
| `url` のユニーク制約 | 同じURLで2件作成 | `IntegrityError` が発生 |
| 曲との多対多関係 | `link.songs.add(song)` | 関係が成立する |

---

### 12. `article` アプリ

**テストファイル案**: `article/tests/test_views.py`

#### 12-1. `ArticlesView` (`/article/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 正常アクセス | GETリクエスト | HTTP 200 |
| 公開記事のみ表示 | `is_open=True/False` の記事が混在 | `is_open=True` の記事のみ表示 |

#### 12-2. `DefaultArticleView` (`/article/<id>/`)

| テストケース | 条件 | 期待結果 |
|---|---|---|
| 存在する記事ID | 有効なarticle_id | HTTP 200 |
| 存在しない記事ID | 無効なarticle_id | HTTP 404 |
| 非公開記事 | `is_open=False` | HTTP 404 または非表示 |

---

## テスト優先度

| 優先度 | 対象 | 理由 |
|---|---|---|
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

## ファイル構成案

```
subekashi/tests/
├── __init__.py
├── TEST_PLAN.md                    # このファイル
├── test_author_migration.py        # 既存
├── song.py                         # 既存（外部依存あり）
├── test_lib_url.py                 # 新規: URL処理ユーティリティ
├── test_lib_song_service.py        # 新規: 曲サービス
├── test_lib_query_filters.py       # 新規: クエリフィルター
├── test_lib_query_utils.py         # 新規: クエリユーティリティ
├── test_lib_author_helpers.py      # 新規: 作者ヘルパー
├── test_lib_song_search.py         # 新規: 検索機能
├── test_forms.py                   # 新規: フォームバリデーション
├── test_views.py                   # 新規: ビュー
├── test_api.py                     # 新規: REST API
├── test_middleware.py              # 新規: ミドルウェア
└── test_models.py                  # 新規: モデル基本動作

article/tests/
└── test_views.py                   # 新規: articleアプリのビュー
```
