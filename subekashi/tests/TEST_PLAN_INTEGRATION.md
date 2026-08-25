# 結合テスト計画書

作成日: 2026-04-10

## 概要

このドキュメントは `subekashi` プロジェクトの**結合テスト**計画をまとめたものです。

### 単体テストとの違い

| 観点 | 単体テスト (`TEST_PLAN_UNIT.md`) | 結合テスト (本書) |
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

#### 1-5. is_questionable 登録時、オリジナル模倣は強制OFF・その他の入力値はそのまま保存される

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/new/` `{title="曲名", authors="作者", is-questionable-manual="on", is-original-manual="on", is-subeana-manual="on"}` |
| 検証: レスポンス | `/songs/<id>/edit` へリダイレクト (302) |
| 検証: Song | `is_questionable == True`、`is_original == False`（強制OFF）、`is_subeana == True`（曲名・作者・URLに加え非公開/削除済み・ネタ曲・インスト・すべあな界隈曲の入力値はそのまま保存される） |

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

#### 2-8. is_questionable 編集時、歌詞・模倣・下書き・オリジナル模倣は強制的に空/OFFで保存される

| 項目 | 内容 |
| --- | --- |
| 前提 | `lyrics`・`imitates`・`is_draft`・`is_original` などが設定済みの曲が存在する |
| 操作 | `POST /songs/<id>/edit/` `{title=..., authors=..., is_questionable=True, lyrics="...", imitate="<id>", is_draft=True, is_original=True}` |
| 検証: レスポンス | `/songs/<id>?toast=edit` へリダイレクト (302) |
| 検証: Song | `is_questionable == True`、`lyrics == ""`、`imitates` が空、`is_draft == False`、`is_original == False`（曲名・作者・URLはそのまま保存） |

#### 2-9. is_questionable 編集時も、非公開/削除済み・ネタ曲・インスト・すべあな界隈曲の入力値はそのまま保存される

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/<id>/edit/` `{title=..., authors=..., is_questionable=True, is_deleted=True, is_joke=True, is_inst=True, is_subeana=True}` |
| 検証: レスポンス | `/songs/<id>?toast=edit` へリダイレクト (302) |
| 検証: Song | `is_questionable == True`、`is_deleted`・`is_joke`・`is_inst`・`is_subeana` がすべて入力通り `True` で保存される |

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

#### 4-3. 正常な問い合わせ送信時にContactレコードが自動登録される

`Contact.create_contact()` によりお問い合わせ内容がDBに自動登録される（実装は `tests/test_views.py` の `ContactViewTest` に追加済み）。

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /contact/` `{category="不具合の報告", detail="テスト詳細文"}` |
| 検証 | `Contact.objects.filter(detail="テスト詳細文").exists() == True` |

#### 4-4. 不正入力時はContactレコードが作成されない

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /contact/` `{category="不具合の報告"}` (`detail` 欠落) |
| 検証 | `Contact.objects.count()` が操作前後で変化しない |

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
| 前提（is_questionable、URLなし） | URL なし・削除されていないが `is_questionable=True` の曲が存在する |
| 操作 | `GET /api/song/?lack=true` |
| 検証 | URLなし条件は `is_questionable` を問わないため、結果に含まれる |
| 前提（is_questionable、歌詞なし） | URL あり・歌詞なしだが `is_questionable=True` の曲が存在する |
| 操作 | `GET /api/song/?lack=true` |
| 検証 | 歌詞なし条件は `is_questionable=False` が必須のため、結果に含まれない |

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

### 11. 別名（AuthorAlias）管理フロー（#992）

**テストファイル**: `tests/test_views.py`（`AuthorAliasesViewTest` / `AuthorAliasNewViewTest` / `AuthorAliasEditViewTest` / `AuthorAliasDeleteViewTest`）

#### 11-1. 別名の新規登録から一覧表示まで

| 項目 | 内容 |
| --- | --- |
| 前提 | `Author(name="foo")` が存在する |
| 操作 | `POST /authors/<foo.id>/aliases/new` に `name="foo_sub"`, `alias_type="past"` |
| 検証 | `/authors/<foo.id>/aliases` へリダイレクト、`AuthorAlias`が作成される |
| 検証 | `History.get_for_author(foo)` に `history_type="new"` のレコードが1件作成される |
| 検証 | `GET /authors/<foo.id>/aliases` に `foo_sub` が表示され、編集・削除リンクを含む |

#### 11-2. 双方向解決が一覧画面に反映される

| 項目 | 内容 |
| --- | --- |
| 前提 | `Author(name="foo")` に別名 `foo_sub` を登録済み |
| 操作 | 後から `Author(name="foo_sub")` を新規登録し、`GET /authors/<foo_sub.id>/aliases` |
| 検証 | 逆方向の別名として `foo` が表示されるが、編集・削除リンクは含まれない |

#### 11-3. 別名の編集

| 項目 | 内容 |
| --- | --- |
| 前提 | `foo` に別名 `foo_sub` が登録済み |
| 操作 | `POST /authors/<foo.id>/aliases/<alias.id>/edit` に `name="foo_sub2"`, `alias_type="sns"` |
| 検証 | 一覧画面へリダイレクト、`AuthorAlias.name`・`alias_type`が更新される |
| 検証 | `History`に `history_type="edit"` のレコードが作成される |

#### 11-4. 別名の削除

| 項目 | 内容 |
| --- | --- |
| 前提 | `foo` に別名 `foo_sub` が登録済み |
| 操作 | `POST /authors/<foo.id>/aliases/<alias.id>/delete` |
| 検証 | 一覧画面へリダイレクト、`AuthorAlias`が削除される |
| 検証 | `History`に `history_type="delete"` のレコードが作成され、`history.author`は削除後も`foo`を指したまま |

#### 11-5. channelリンクとSong検索への反映

| 項目 | 内容 |
| --- | --- |
| 前提 | `Song1(author=foo)`, `Song2(author=foo_sub)` が存在し、`foo`に別名`foo_sub`(`alias_type="past"`)を登録 |
| 操作 | `GET /authors/<foo.id>/aliases` |
| 検証 | `foo_sub`の項目に `/channel/foo_sub/` へのリンクが含まれる |
| 操作 | `GET /songs/?keyword=foo_sub` |
| 検証 | `Song1`・`Song2`の両方がヒットする（#990の別名フィルターとの連携） |

#### 11-6. Discord通知（仕様変更）

`send_discord()` をモックして検証する。`SEND_DISCORD=False` により通常のテストでは実送信されないため、
運用上の可視性を確認する目的でモックを使い明示的にテストする。

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /authors/<foo.id>/aliases/new` |
| 検証 | `send_discord()` がNEW_DISCORD_URL宛に呼ばれ、別名名・作者名を含む |
| 操作 | 実質的な変更を伴う `POST /authors/<foo.id>/aliases/<alias.id>/edit` |
| 検証 | `send_discord()` がNEW_DISCORD_URL宛に呼ばれる |
| 操作 | `POST /authors/<foo.id>/aliases/<alias.id>/delete` |
| 検証 | `send_discord()` がNEW_DISCORD_URL宛に呼ばれ、削除対象の別名名を含む（新規・編集と同じ通知先） |
| 操作 | `send_discord()` が失敗（`False`を返す）した状態で新規登録・削除 |
| 検証 | 新規登録: 作成したAuthorAliasがロールバックされHTTP 500。削除: AuthorAliasは削除されずHTTP 500（通知できた場合のみ実行される設計） |

#### 11-7. 変更なし編集はHistory・Discord通知をスキップ

| 項目 | 内容 |
| --- | --- |
| 前提 | `foo` に別名 `foo_sub`(`alias_type="past"`) が登録済み |
| 操作 | `POST /authors/<foo.id>/aliases/<alias.id>/edit` に変更前と同じ `name="foo_sub"`, `alias_type="past"` |
| 検証 | 一覧画面へリダイレクトはするが、`History`は作成されず`send_discord()`も呼ばれない（SongEditViewと同様の挙動） |

#### 11-8. 重複チェックのTOCTOU対策

| 項目 | 内容 |
| --- | --- |
| 前提 | `foo` に別名 `foo_sub` が既に登録済み |
| 操作 | `AuthorAliasForm.clean_name` の重複チェックをモックでバイパスした状態で、同じ `name="foo_sub"` を新規登録POST |
| 検証 | DB制約(`IntegrityError`)を`AuthorAliasNewView`が捕捉し、500エラーにならずHTTP 200のままフォームエラーが表示される。`AuthorAlias`は重複作成されない |

#### 11-9. 一番有名な名義の選択から曲登録正規化まで（#1008、#1029）

**テストファイル**: `tests/test_views.py`（`AuthorPrimaryNameSetViewTest`、`AuthorPrimaryNameConfirmViewTest`）、`tests/test_lib_author_helpers.py`

| 項目 | 内容 |
| --- | --- |
| 前提 | `Author(name="foo")` に別名 `foo_old`(`alias_type="past"`) が登録済み。`foo_old`という名前の別Authorは存在しない |
| 操作 | `GET /authors/<foo.id>/aliases/primary/confirm/` に `name="foo_old"` |
| 検証 | 変更内容の確認画面（対象Songの一覧＋「の名義を『foo_old』に変更されます」）が表示される |
| 操作 | 確認画面から `POST /authors/<foo.id>/aliases/primary` に `name="foo_old"` |
| 検証 | `Author.name`が`"foo_old"`に入れ替わり、旧名`"foo"`が新たな`past`別名として再登録される。`?toast=primary`付きで一覧画面へリダイレクト |
| 検証 | `History`に`history_type="edit"`のレコードが作成され、`send_discord()`が変更前後の名前を含む内容で呼ばれる |
| 操作（正規化の確認） | 上記の状態変更後、`POST /songs/new/` の`authors`に旧名`"foo"`を指定して曲登録 |
| 検証 | `get_or_create_authors()`が`"foo"`を`past`別名として解決し、新規Authorを作らず`Author(name="foo_old")`（同一のAuthor行）に紐づく。redirect先URLに`primary_name_normalized=1`が付与され、遷移先画面でinfoトーストが表示される |
| 操作（衝突ケース、#1029で仕様変更） | 選択したpast別名の名前と完全一致する別Author（conflicting_author）が既に存在する状態で `POST /authors/<foo.id>/aliases/primary` に `name="foo_old"` |
| 検証 | かつては選択自体をブロックしていたが、#1029でconflicting_authorのSong・AuthorLink・AuthorAliasを全て`foo`に付け替えた上でconflicting_authorを削除する自動統合（マージ）に変更された。`Author.name`が`"foo_old"`に変わり、`?toast=primary`付きで一覧画面へリダイレクトされる |

---

### 12. 生成結果の単語クリック入れ替えフロー（#1053）

**テストファイル**: `tests/test_views.py`（`AiViewTest` / `AiResultViewTest`）、`tests/test_api.py`（`WordCandidatesViewTest` / `AiWordSwapViewTest`）

単語クリック入れ替え機能は `ai/result/`（生成結果）にのみ提供する（方針転換により`ai/`＝最高評価の歌詞では提供しない）。`ai/result/`の表示（歌詞の単語分割・クリック可否の判定） → 候補取得API → 入れ替えPOSTによる新規`Ai`作成までの一連の流れを、HTTPリクエスト単位で連携させて検証する。ブラウザ側のクリック操作・ポップアップ表示（`word_swap.js`）自体はDjangoテストの対象外のため、実サーバー起動 + `curl`/Playwrightによる手動確認で代替した（本PR作成時に実施済み）。

#### 12-1. 表示から候補取得、入れ替え保存までの一連の流れ

| 項目 | 内容 |
| --- | --- |
| 前提 | `Ai(lyrics="私は走る", score=0, genetype="model")`、`Word(word="走る", hinshi="動詞", candidate="駆ける")`が存在する |
| 操作1 | `GET /ai/result/` |
| 検証1 | レスポンスに`走る`が`class="word-token"`（クリック可能）として含まれる |
| 操作2 | `GET /api/word/candidates/?word=走る&hinshi=動詞` |
| 検証2 | `{"candidates": ["駆ける"]}` が返る |
| 操作3 | `POST /api/ai/swap/` に `{"base_id": <ai.id>, "token_index": 2, "candidate": "駆ける"}` |
| 検証3 | HTTP 201、`lyrics="私は駆ける"`, `score=0` の新規`Ai`レコードが作成される |
| 検証4 | 元の`Ai(lyrics="私は走る")`は変更されない |

#### 12-2. 不正な入れ替えリクエストの拒否

| 項目 | 内容 |
| --- | --- |
| 前提 | 12-1と同じ |
| 操作 | `POST /api/ai/swap/` に `Word`に存在しない`candidate`を指定 |
| 検証 | HTTP 400、`Ai`レコードは作成されない（`Ai.objects.count()`が変化しない） |

#### 12-3. 最高評価の歌詞（`ai/`）は単語入れ替え機能を提供しない（方針転換）

| 項目 | 内容 |
| --- | --- |
| 前提 | `Ai(lyrics="私は走る", score=5, genetype="model")`、`Word(word="走る", hinshi="動詞", candidate="駆ける")`が存在する |
| 操作 | `GET /ai/` |
| 検証 | Word候補が存在していても`class="word-token"`は含まれず、歌詞はプレーンテキストで表示される |

#### 12-4. 同じ入れ替え結果の重複防止

| 項目 | 内容 |
| --- | --- |
| 前提 | 12-1と同じ |
| 操作 | 同一の`base_id`・`token_index`・`candidate`で`POST /api/ai/swap/`を2回実行 |
| 検証 | 2回とも同じ`Ai`レコードのidが返り、新規レコードは1件しか作成されない |

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
