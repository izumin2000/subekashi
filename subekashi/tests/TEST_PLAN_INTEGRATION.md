# 結合テスト計画書

作成日: 2026-04-10

## 概要

このドキュメントは `subekashi` プロジェクトの**結合テスト**計画をまとめたものです。

### 単体テストとの違い

| 観点 | 単体テスト (`TEST_PLAN.md`) | 結合テスト (本書) |
| --- | --- | --- |
| 対象 | 関数・クラス単体の動作 | 複数コンポーネントが連携する一連の操作 |
| DB | モックまたは最小限の準備 | 実際のDBを使い、操作後のDB状態を検証 |
| 検証内容 | 戻り値・例外 | HTTPレスポンス ＋ DB状態の変化 |
| 外部依存 | mock.patch で置換 | Discord は `SEND_DISCORD=False` で自動無効化、YouTube API は必要時にモック |

### 外部依存の扱い

| 外部依存 | 結合テストでの扱い |
| --- | --- |
| `send_discord()` | `SEND_DISCORD=False`（local_settings）により自動でスキップ。モック不要 |
| `get_youtube_api()` | YouTube URL を POST しないシナリオで回避。YouTube URL を使う場合は `@patch` でモック |
| `get_ip()` | Django テストクライアントの `REMOTE_ADDR` を利用 |

---

## テストシナリオ一覧

---

### 1. 曲登録フロー

**テストファイル案**: `tests/integration/test_flow_song_new.py`

ビュー層 → `get_or_create_authors` → `create_song_with_relations` → `History.create_for_song` の全連携を検証する。

#### 1-1. 正常な曲登録

| 項目 | 内容 |
| --- | --- |
| 前提 | DB が空 |
| 操作 | `POST /songs/new/` `{title="新曲タイトル", authors="作者A", url=""}` |
| 検証: レスポンス | `/songs/<id>/edit` へリダイレクト (302) |
| 検証: Song | `Song.objects.filter(title="新曲タイトル")` が 1 件存在する |
| 検証: Author | `Author.objects.filter(name="作者A")` が 1 件作成されている |
| 検証: Song-Author | `song.authors.all()` に作者 A が含まれる |
| 検証: Editor | `Editor.objects.count()` が 1 件増加している |
| 検証: History | `History.objects.filter(history_type="new")` が 1 件作成されている |

#### 1-2. 同名作者は重複作成されない

| 項目 | 内容 |
| --- | --- |
| 前提 | `Author(name="既存作者")` が DB に存在する |
| 操作 | `POST /songs/new/` `{title="新曲", authors="既存作者", url=""}` |
| 検証 | `Author.objects.filter(name="既存作者").count() == 1`（新規作成されない） |

#### 1-3. 非 YouTube URL はエラー

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/new/` `{title="新曲", authors="作者", url="https://example.com/video"}` |
| 検証: レスポンス | HTTP 200、`context["error"]` に "YouTube" を含む |
| 検証: DB | `Song.objects.count() == 0`（登録されていない） |

#### 1-4. 重複 URL はエラー

| 項目 | 内容 |
| --- | --- |
| 前提 | `SongLink(url="https://youtu.be/abc1234abcd")` が曲に紐付いている |
| 操作 | `POST /songs/new/` `{url="https://youtu.be/abc1234abcd", ...}` |
| 検証: レスポンス | HTTP 200、`context["error"]` に重複を示すメッセージを含む |
| 検証: DB | 新たな Song は作成されていない |

---

### 2. 曲編集フロー

**テストファイル案**: `tests/integration/test_flow_song_edit.py`

ビュー層 → `update_song` → `build_edit_song_discord_text` → `History.create_for_song` の全連携を検証する。

#### 2-1. タイトル変更

| 項目 | 内容 |
| --- | --- |
| 前提 | `Song(title="旧タイトル")` が存在。`Author(name="作者A")` が紐付いている |
| 操作 | `POST /songs/<id>/edit/` `{title="新タイトル", authors="作者A", ...}` |
| 検証: レスポンス | `/songs/<id>?toast=edit` へリダイレクト (302) |
| 検証: Song | `Song.objects.get(pk=id).title == "新タイトル"` |
| 検証: History | `History.objects.filter(history_type="edit").count() == 1` |

#### 2-2. 作者の変更

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲に `Author(name="旧作者")` が紐付いている |
| 操作 | `POST /songs/<id>/edit/` `{authors="新作者", title=...}` |
| 検証 | `song.authors.all()` に "新作者" が含まれ、"旧作者" が含まれない |
| 検証 | `Author.objects.filter(name="新作者").count() == 1`（新規作成される） |

#### 2-3. URL の追加

| 項目 | 内容 |
| --- | --- |
| 前提 | URL を持たない曲が存在する |
| 操作 | `POST /songs/<id>/edit/` `{url="https://youtu.be/newurl00001", ...}` |
| 検証 | `SongLink.objects.filter(url="https://youtu.be/newurl00001")` が作成されている |
| 検証 | `song.songlink_set.count() == 1` |

#### 2-4. URL の削除 — 他曲が使用していない場合は SongLink ごと削除

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲に `SongLink(url="https://youtu.be/removeurl001")` が紐付いている（他の曲は使っていない） |
| 操作 | `POST /songs/<id>/edit/` `{url="", ...}` |
| 検証 | `SongLink.objects.filter(url="https://youtu.be/removeurl001").count() == 0`（完全削除） |

#### 2-5. URL の削除 — 他曲が使用している場合は M2M のみ解除

| 項目 | 内容 |
| --- | --- |
| 前提 | `SongLink` が 2 曲に紐付いている |
| 操作 | 1 曲だけ URL を削除するよう編集 |
| 検証 | `SongLink` レコード自体は残る（他の曲への紐付けが残るため） |
| 検証 | 編集した曲の M2M だけ解除されている |

#### 2-6. 変更なし — History が作成されない

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲が存在する |
| 操作 | `POST /songs/<id>/edit/` に現在と同じ値を送信 |
| 検証 | `History.objects.count() == 0`（差分なし → 履歴不要） |

#### 2-7. ロック済み曲はリダイレクト

| 項目 | 内容 |
| --- | --- |
| 前提 | `song.is_lock = True` |
| 操作 | `GET /songs/<id>/edit/` または `POST /songs/<id>/edit/` |
| 検証 | `/songs/<id>?toast=lock` へリダイレクト (302) |
| 検証 | Song は変更されていない |

---

### 3. 削除申請フロー

**テストファイル案**: `tests/integration/test_flow_song_delete.py`

ビュー層 → `Editor.get_or_create_from_ip` → `History.create_for_song` の連携を検証する。

#### 3-1. 正常な削除申請

| 項目 | 内容 |
| --- | --- |
| 前提 | 削除されていない曲が存在する |
| 操作 | `POST /songs/<id>/delete/` `{reason="著作権上の理由"}` |
| 検証: レスポンス | `/songs/<id>?toast=delete` へリダイレクト (302) |
| 検証: Song | `Song.is_deleted` は変化していない（申請のみ） |
| 検証: History | `History(history_type="delete")` が 1 件作成されている |
| 検証: Editor | `Editor.objects.count()` が 1 件増加（または既存が再利用）している |

#### 3-2. 削除理由が空はエラー

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/<id>/delete/` `{reason=""}` |
| 検証: レスポンス | HTTP 200、`context["error"]` にエラーメッセージ |
| 検証: DB | `History.objects.count() == 0` |

#### 3-3. ロック済み曲はリダイレクト

| 項目 | 内容 |
| --- | --- |
| 前提 | `song.is_lock = True` |
| 操作 | `POST /songs/<id>/delete/` |
| 検証 | `/songs/<id>?toast=lock` へリダイレクト |
| 検証 | `History.objects.count() == 0` |

---

### 4. お問い合わせフロー

**テストファイル案**: `tests/integration/test_flow_contact.py`

#### 4-1. 正常な問い合わせ送信

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /contact/` `{category="不具合の報告", detail="詳細内容"}` |
| 検証 | HTTP 200、`context["result"] == "ok"` |

#### 4-2. 不正入力

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /contact/` `{category="不具合の報告"}` (`detail` 欠落) |
| 検証 | HTTP 200、`context["result"]` にエラーメッセージが含まれる |

---

### 5. 楽曲検索・API フロー

**テストファイル案**: `tests/integration/test_flow_search.py`

ビュー (`SongsView`) と API (`SongAPI`) 双方で検索・ページネーションが一貫して動作するかを検証する。

#### 5-1. キーワード検索のエンドツーエンド

| 項目 | 内容 |
| --- | --- |
| 前提 | `Song(title="検索対象曲")` と `Song(title="関係ない曲")` が存在する |
| 操作 | `GET /api/song/?keyword=検索対象` |
| 検証 | `data["result"]` に `title="検索対象曲"` が含まれ、`title="関係ない曲"` が含まれない |
| 検証 | `data["count"] == 1` |

#### 5-2. ページネーションのエンドツーエンド

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲が 25 件存在する |
| 操作 | `GET /api/song/?page=1&size=10` → `GET /api/song/?page=3&size=10` |
| 検証 page1 | `len(data["result"]) == 10` |
| 検証 page3 | `len(data["result"]) == 5` |
| 検証 統計 | `data["count"] == 25`, `data["max_page"] == 3` |

#### 5-3. `is_deleted` フィルターのエンドツーエンド

| 項目 | 内容 |
| --- | --- |
| 前提 | `Song(is_deleted=True)` と `Song(is_deleted=False)` が存在する |
| 操作 | `GET /api/song/?is_deleted=true` |
| 検証 | 削除済み曲のみ返される |

#### 5-4. 未完成曲フィルターのエンドツーエンド

| 項目 | 内容 |
| --- | --- |
| 前提 | URL なし・歌詞なし曲と、URL あり・歌詞あり曲が存在する |
| 操作 | `GET /api/song/?lack=true` |
| 検証 | 未完成曲のみ返される |

#### 5-5. SongsView ページでの検索

| 項目 | 内容 |
| --- | --- |
| 操作 | `GET /songs/?keyword=検索対象` |
| 検証 | HTTP 200、`context` に絞り込まれた曲が含まれる |

---

### 6. 作者管理フロー

**テストファイル案**: `tests/integration/test_flow_author.py`

#### 6-1. 複数の曲に同一作者が紐付く

| 項目 | 内容 |
| --- | --- |
| 前提 | DB が空 |
| 操作 | 曲 A と曲 B を別々に登録（どちらも `authors="共通作者"`） |
| 検証 | `Author.objects.filter(name="共通作者").count() == 1`（重複なし） |
| 検証 | 曲 A と曲 B どちらにも同じ Author が紐付いている |

#### 6-2. 作者ページ (`/authors/<id>/`) の表示

| 項目 | 内容 |
| --- | --- |
| 前提 | 作者に曲が紐付いている |
| 操作 | `GET /authors/<id>/` |
| 検証 | HTTP 200、作者名がレスポンスに含まれる |

#### 6-3. `/channel/<name>/` → 作者ページへのリダイレクト

| 項目 | 内容 |
| --- | --- |
| 前提 | `Author(name="テストチャンネル")` が存在する |
| 操作 | `GET /channel/テストチャンネル/` |
| 検証 | `/authors/<id>/` へリダイレクト (302) |

---

### 7. 模倣関係フロー

**テストファイル案**: `tests/integration/test_flow_imitate.py`

#### 7-1. 模倣関係の登録

| 項目 | 内容 |
| --- | --- |
| 前提 | 原曲と模倣曲が存在する |
| 操作 | `POST /songs/<模倣曲id>/edit/` `{imitate="<原曲id>", ...}` |
| 検証 | `模倣曲.imitates.all()` に原曲が含まれる |

#### 7-2. 模倣関係の解除

| 項目 | 内容 |
| --- | --- |
| 前提 | 模倣関係が設定済み |
| 操作 | `POST /songs/<模倣曲id>/edit/` `{imitate="", ...}` |
| 検証 | `模倣曲.imitates.all()` が空 |

---

### 8. 歌詞の CRLF 正規化フロー

**テストファイル案**: `tests/integration/test_flow_lyrics.py`

#### 8-1. CRLF が LF に正規化される

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲が存在する |
| 操作 | `POST /songs/<id>/edit/` `{lyrics="一行目\r\n二行目", ...}` |
| 検証 | `Song.objects.get(pk=id).lyrics == "一行目\n二行目"`（CRLF が LF に変換） |
| 備考 | `Song.save()` でモデルレベルの正規化が実行される |

---

### 9. SongHistoryView フロー

**テストファイル案**: `tests/integration/test_flow_history.py`

#### 9-1. 編集履歴の表示

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲が存在し、編集履歴が 1 件ある |
| 操作 | `GET /songs/<id>/history/` |
| 検証 | HTTP 200 |

#### 9-2. 編集 → 履歴ページで確認

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲が存在する |
| 操作 | `POST /songs/<id>/edit/` でタイトルを変更 → `GET /songs/<id>/history/` |
| 検証 | 履歴ページに更新されたタイトルまたは変更内容が含まれる |

---

### 10. YouTube API 連携フロー（モック使用）

**テストファイル案**: `tests/integration/test_flow_youtube.py`

YouTube Data API は外部サービスのため、`unittest.mock.patch` でモックする。

#### 10-1. YouTube URL 登録時に API から情報取得

| 項目 | 内容 |
| --- | --- |
| モック対象 | `subekashi.views.song_new.get_youtube_api` → `{"title": "YT動画タイトル", "author": "YTチャンネル名", ...}` を返す |
| 操作 | `POST /songs/new/` `{url="https://youtu.be/dQw4w9WgXcQ", authors="", title=""}` |
| 検証 | `Song.objects.get(...).title == "YT動画タイトル"` |
| 検証 | `Author.objects.filter(name="YTチャンネル名").count() == 1` |

---

## テスト実装の方針

### ディレクトリ構成（案）

```
subekashi/tests/
├── integration/
│   ├── __init__.py
│   ├── test_flow_song_new.py
│   ├── test_flow_song_edit.py
│   ├── test_flow_song_delete.py
│   ├── test_flow_contact.py
│   ├── test_flow_search.py
│   ├── test_flow_author.py
│   ├── test_flow_imitate.py
│   ├── test_flow_lyrics.py
│   ├── test_flow_history.py
│   └── test_flow_youtube.py     # YouTube API モック使用
└── ... (既存の単体テスト)
```

### 基本方針

1. **テストクラス**: `django.test.TestCase` を使用（各テスト後に DB を自動ロールバック）
2. **テストクライアント**: `from django.test import Client` を使用してフル HTTP スタックを通す
3. **StaticFilesStorage**: `@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")` で ManifestStaticFilesStorage を無効化
4. **Discord**: `SEND_DISCORD=False` により自動でスキップ。追加のモック不要
5. **YouTube API**: YouTube URL を含まないシナリオで回避。含む場合は `@patch("subekashi.views.song_new.get_youtube_api", return_value={...})` を使用
6. **DB 状態の検証**: `assertX` の前後で `Model.objects.count()` や `Model.objects.get()` を使い、副作用も含めて確認する

### 単体テストと結合テストの実行方法

```bash
# 単体テストのみ
python manage.py test subekashi.tests

# 結合テストのみ
python manage.py test subekashi.tests.integration

# 全テスト
python manage.py test subekashi.tests article.tests
```

---

## 優先度

| 優先度 | シナリオ | 理由 |
| --- | --- | --- |
| **高** | 曲登録フロー (1) | 中核機能。Song/Author/SongLink/History が正しく連携するかを一括確認 |
| **高** | 曲編集フロー (2) | update_song の副作用（SongLink の追加・削除）は単体テストでカバーしにくい |
| **高** | 楽曲検索・API フロー (5) | ページネーション + フィルターの組み合わせはE2Eで確認が必要 |
| **中** | 削除申請フロー (3) | 単体テストでほぼカバー済みだが、DB 書き込みの確認が必要 |
| **中** | 作者管理フロー (6) | get_or_create の重複防止は実 DB で確認が重要 |
| **中** | YouTube API 連携フロー (10) | 外部 API との連携は結合テストでしか確認できない |
| **低** | 模倣関係フロー (7) | M2M の操作は比較的単純 |
| **低** | 歌詞 CRLF 正規化フロー (8) | モデルのsave()で動作。既存モデルテストで一部カバー済み |
| **低** | 履歴フロー (9) | 表示確認のみ |
