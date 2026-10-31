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
| `get_ip()` | `X-Real-IP` を付けない場合は Django テストクライアントの `REMOTE_ADDR` を利用（#1189） |

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
| 操作 | `POST /songs/new/` `{title="タイトル", authors="作者", is-questionable-manual="on", is-original-manual="on", is-subeana-manual="on"}` |
| 検証: レスポンス | `/songs/<id>/edit` へリダイレクト (302) |
| 検証: Song | `is_questionable == True`、`is_original == False`（強制OFF）、`is_subeana == True`（タイトル・作者・URLに加え非公開/削除済み・ネタ曲・インスト・すべあな界隈曲の入力値はそのまま保存される） |

#### 1-6. カテゴリを指定して登録（#423）

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/new/` `{title="タイトル", authors="作者", category="otomad"}` |
| 検証: レスポンス | `/songs/<id>/edit` へリダイレクト (302) |
| 検証: Song | `category == "otomad"`（`category` を送らない場合は `"song"`、選択肢にない値はエラーでSongは作成されない） |

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
| 検証: Song | `is_questionable == True`、`lyrics == ""`、`imitates` が空、`is_draft == False`、`is_original == False`（タイトル・作者・URLはそのまま保存） |

#### 2-9. is_questionable 編集時も、非公開/削除済み・ネタ曲・インスト・すべあな界隈曲の入力値はそのまま保存される

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/<id>/edit/` `{title=..., authors=..., is_questionable=True, is_deleted=True, is_joke=True, is_inst=True, is_subeana=True}` |
| 検証: レスポンス | `/songs/<id>?toast=edit` へリダイレクト (302) |
| 検証: Song | `is_questionable == True`、`is_deleted`・`is_joke`・`is_inst`・`is_subeana` がすべて入力通り `True` で保存される |

#### 2-10. カテゴリの変更（#423）

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/<id>/edit/` `{title=..., authors=..., category="omnibus"}` |
| 検証: レスポンス | `/songs/<id>?toast=edit` へリダイレクト (302) |
| 検証: Song | `category == "omnibus"`。`category` を送らない場合は編集前のカテゴリのまま。カテゴリが曲以外でも、送信された歌詞はそのまま保存される（歌詞の入力欄は `song_edit.js` で非表示にするだけ） |
| 検証: History | `changes` に `["カテゴリ", "曲", "総集編"]`（選択肢の表示名）が含まれる |

#### 2-11. ビリビリ動画のURLを揃えて保存し、同じ動画のURLを重複として扱う（#1246）

| 項目 | 内容 |
| --- | --- |
| 操作 | `POST /songs/<id>/edit/` `{url="https://www.bilibili.com/video/av417727107/?spm_id_from=...,https://www.bilibili.com/video/BV1in4y1Q7qw?p=2&vd_source=...", ...}` |
| 検証: レスポンス | `/songs/<id>?toast=edit` へリダイレクト (302) |
| 検証: SongLink | `https://bilibili.com/video/BV1qV411J7Kq`・`https://bilibili.com/video/BV1in4y1Q7qw?p=2` で保存される（av番号はBV番号に変換し、2パート目以降の `p` のみ残す） |
| 検証: 重複 | 別の曲に `https://bilibili.com/video/BV1qV411J7Kq` が紐付いているとき、`https://www.bilibili.com/video/av417727107/` を送ると HTTP 200、"既に登録されています" のエラーでURLは追加されない。画面のJSが重複の判定に使う `GET /api/songlink/?url=` も、av番号・`www.`・`m.`・末尾の `/`・クエリの違うURLで同じ `SongLink` を返し、`?p=2` のURLでは返さない |

#### 2-12. URLの重複を許可して曲を保存したとき、そのURLを元から持つ曲の編集履歴に残す（#1282、#1285）

URLの重複を許可するのは、曲を保存するPOSTのときだけにする。GETで開いただけでは許可しない（#1285）。

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲Aに `SongLink(url="https://youtu.be/dupallow123")`（`allow_dup=False`）が紐付いている。曲Bがある |
| 操作 | `POST /songs/new/` `{url="https://youtu.be/dupallow123", allow_dup_url="https://youtu.be/dupallow123"}`（`get_youtube_api` はモック）、または `POST /songs/<曲Bのid>/edit/` `{title=..., authors=..., url="https://youtu.be/dupallow123", allow_dup_url="https://youtu.be/dupallow123"}` |
| 検証: レスポンス | 302 |
| 検証: SongLink | `allow_dup == True` で、曲Aと保存した曲（新しい曲または曲B）の両方が紐付く |
| 検証: History | 曲Aに `history_type="edit"` のHistoryが1件でき、タイトルは「<曲Aのタイトル>のURLの重複を許可」、`changes` は `[["種類", "内容"], ["重複許可したURL", "https://youtu.be/dupallow123"]]`、編集者はリクエストのIPのEditor。保存した曲には「重複を許可」のHistoryはできない |
| 検証: 既に許可したURL | `allow_dup=True` のURLでは、Historyは増えない |
| 検証: 編集している曲だけのURL | `POST /songs/<曲Bのid>/edit/` で、曲Bにしか紐付いていない `allow_dup=False` のURLを `allow_dup_url` に付けても、`allow_dup == False` のままで、「重複を許可」のHistoryもDiscordへの通知もできない（重複していないURLは許可しない） |
| 検証: Discord | 重複許可したURLの通知を `CONTACT_DISCORD_URL` に1回送る（曲を保存した後） |
| 検証: GET | `GET /songs/new/?allow_dup_url=...`・`GET /songs/<曲Bのid>/edit/?allow_dup_url=...` は HTTP 200で、`allow_dup`・History・Discordは変わらない |
| 検証: `allow_dup_url` なし | `allow_dup_url` を送らないと HTTP 200で "既に登録されています" のエラー。`allow_dup` も History も変わらない |
| 検証: 保存できなかったとき | 曲を保存できずエラーになったときは、`allow_dup_url` を送っていても `allow_dup == False` のままで、HistoryもDiscordへの通知もできない |

---

### 3. 削除フロー

**テストファイル案**: `tests/integration/test_flow_song_delete.py`

ビュー層 → `remove_song` → `Editor.get_or_create_from_ip` → `History.create_for_song` → `send_discord` の連携を検証する。
削除申請ではなく、送信するとすぐに曲を論理削除する（#1239）。

#### 3-1. 正常な削除

| 項目 | 内容 |
| --- | --- |
| 前提 | 削除されていない曲が存在する |
| 操作 | `POST /songs/<id>/delete/` `{reason="著作権上の理由"}` |
| 検証: レスポンス | `/?toast=delete`（トップ）へリダイレクト (302) |
| 検証: Song | `Song.is_removed` が `True` になる（`Song.is_deleted` は変化しない）。作者・URL・模倣元は残る |
| 検証: History | `History(history_type="delete", title="<タイトル>を削除")` が 1 件作成されている |
| 検証: Editor | `Editor.objects.count()` が 1 件増加（または既存が再利用）している |
| 検証: Discord | 新規登録・編集と同じNEW_DISCORD_URL宛に、新規作成と同じ形式（`削除されました`・曲のページのURL・空行）で始まり、タイトル・作者・削除理由・編集者を含む文面を送る |
| 検証: 表示 | 曲のページ・編集・削除・編集履歴のページが、「<曲名>のページは削除されました」と削除理由、「削除を取り消す」ボタンのあるページ（HTTP 410、#1264）になり、検索・API・作者のページ・模倣元/模倣曲の一覧・統計・サイトマップに含まれない。編集履歴の一覧では曲へのリンクの代わりに「この曲または作者は削除されました」と表示される |
| 検証: URL | 削除した曲だけに紐づくURLは、別の曲に登録できる（`validate_song_url`・`/api/songlink/`） |

#### 3-1-1. 削除した曲の復元（手動）

| 項目 | 内容 |
| --- | --- |
| 操作 | 管理サイトの曲の変更画面で `is_removed` のチェックを外して保存する |
| 検証 | 曲のページ等に再び表示され、作者・URL・模倣関係も削除前のまま戻る |

#### 3-1-2. 削除の取り消し（#1264）

ビュー層 → `get_restore_conflict_songs` → `restore_song` → `History.create_for_song` → `send_discord` の連携を検証する。

| 項目 | 内容 |
| --- | --- |
| 前提 | 3-1 で削除した曲（削除理由「誤って登録」） |
| 操作 | 削除した曲のページで取り消し理由（必須）を入力して「削除を取り消す」ボタン（`POST /songs/<id>/restore/` `{reason="誤って削除したため"}`） |
| 検証: 表示（取り消す前） | 曲のページに「削除理由：誤って登録」と、`/songs/<id>/restore/` にPOSTするフォーム（`csrfmiddlewaretoken` 付き、取り消し理由の入力欄は`required`）が表示される |
| 検証: 理由が空 | 理由を送らない・空白だけの場合は取り消さず、曲のページ（HTTP 410）に「取り消し理由を入力してください。」のエラーを表示する。Historyの作成・Discordへの通知もしない（#1275） |
| 検証: ボタンの無効化（Playwrightで確認） | 取り消し理由が空・空白だけの間は「削除を取り消す」ボタンが`disabled`で、無効の見た目（背景`#666`・文字`#aaa`、`cursor: not-allowed`）になる。理由を入力すると押せるようになり、消すと再び押せなくなる。CSP違反・JSのエラーが出ない（#1275） |
| 検証: レスポンス | `/songs/<id>?toast=restore` へリダイレクト (302)。曲のページに「削除を取り消しました。」のトーストが出る |
| 検証: Song | `Song.is_removed` が `False` に戻り、曲のページがHTTP 200になる。作者・URL・模倣関係も削除前のまま戻る |
| 検証: History | `History(history_type="restore", title="<タイトル>の削除を取り消し", changes=["理由", "誤って削除したため"])` が作成され、削除と取り消しの両方の履歴が残る。編集履歴の一覧では再び曲へリンクする |
| 検証: Discord | NEW_DISCORD_URL宛に、削除と同じ形式（`削除が取り消されました`・曲のページのURL・空行）で始まり、タイトル・作者・取り消し理由・編集者を含む文面を送る。送信に失敗した場合も取り消しは行い、`?toast=restore_notify_error` にリダイレクトする |
| 検証: 取り消せない曲 | ロックされた曲・URLが削除していない他の曲に登録されている曲は、ボタンを表示せず理由（URLの場合は登録している曲へのリンク）を表示する。POSTしても取り消さず、Historyの作成・Discordへの通知もしない |
| 検証: 同時に押す | 曲の行をロック（`select_for_update`）してから確認・取り消しを行うため、同時に2回送っても取り消し・Historyの作成・Discordへの通知は1回だけ（SQLiteでは実行しない） |
| 検証: 編集履歴 | 曲の編集履歴のページで、削除と取り消しの履歴はどちらも理由の表（`delete-table`）を表示する。理由を入力しなかった頃の取り消しの履歴（`changes=None`）は変更内容の表を表示せず、崩れない（#1275） |

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
| 検証 | `History.objects.count() == 0`、`Song.is_removed` は `False` のまま |

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

#### 5-4-1. カテゴリの検索（#423）

| 項目 | 内容 |
| --- | --- |
| 前提 | カテゴリが曲・アレンジ・ネタ動画の曲が存在する |
| 操作 | `GET /api/song/?categorys=arrange,meme` |
| 検証 | アレンジ・ネタ動画の曲のみ返される（`mediatypes` と同様にカンマ区切りで複数指定できる）。曲の検索画面（`/api/html/song_cards`）では「カテゴリが有効です」が表示される |
| 操作 | `GET /api/song/?categorys=~song,~meme` |
| 検証 | 先頭に~を付けたカテゴリ（「以外」）の曲を除き、アレンジの曲のみ返される |

#### 5-4-2. カテゴリの選択の保存（#423）

| 項目 | 内容 |
| --- | --- |
| 前提 | 設定「検索の選択肢の保存」が保存（`is_saved_select=on`） |
| 操作 | 検索画面でカテゴリの指定なし・のみ・以外を変更する（songs.jsが `POST /songs/` `{categorys="arrange,~meme"}` を送る）→ `GET /songs/` |
| 検証 | `search_categorys` cookieに保存され、URLクエリが無い検索画面・トップ画面の「全て表示」の検索で、アレンジの「のみ」・ネタ動画の「以外」のラジオボタンが選択される。曲ページのタグのリンク（`GET /songs/?categorys=...`）では保存した選択を上書きしない。保存しない設定（`is_saved_select=off`）では保存した選択を使わない |

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

#### 6-4. 作者ページの並び替えの保存（#606）

実装: `tests/test_views.py` の `AuthorViewTest.test_selected_sort_applies_to_other_authors`

| 項目 | 内容 |
| --- | --- |
| 前提 | 作者 A・B が存在し、「検索の選択肢の保存」の設定が未設定（保存） |
| 操作 | `GET /authors/<A.id>/?sort=-like` の後、同じクライアントで `GET /authors/<B.id>/` |
| 検証 | 1回目のレスポンスで `author_sort` cookie が保存され、2回目は URL クエリなしでも高評価数の多い順で表示される |

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

#### 10-2. YouTube上で削除・非公開の動画のURLで登録するとその趣旨のトーストを表示（#886）

**テストファイル**: `tests/test_views.py`（`SongNewViewTest`）

| 項目 | 内容 |
| --- | --- |
| モック対象 | `subekashi.views.song_new.get_youtube_api` → `{}`（削除・非公開）を返す |
| 操作 | `POST /songs/new/` `{url="https://youtu.be/aaaaaaaaaaa", is-deleted-auto="on"}` |
| 検証: レスポンス | HTTP 200、「作者は空白にできません。」ではなく、動画が削除・非公開であることと「タイトルと作者から登録」で「非公開/削除済み」にチェックを入れて登録するよう案内するエラーがトーストで表示される |
| 検証: DB | Song は作成されていない |

#### 10-3. インターネットに接続できずYouTubeから動画の情報を取得できない場合（#886）

**テストファイル**: `tests/test_views.py`（`SongNewViewTest`）

| 項目 | 内容 |
| --- | --- |
| モック対象 | `subekashi.lib.youtube.build`（APIの呼び出しが`socket.timeout`を送出）。`get_youtube_api`はモックせず、`YoutubeApiError`に変換されることも含めて確認する |
| 操作 | `POST /songs/new/` `{url="https://youtu.be/aaaaaaaaaaa"}` |
| 検証: レスポンス | HTTP 200、インターネットに接続できなかった可能性を伝えるエラーが表示され、動画が削除・非公開であるとは伝えない（「削除」を含まない） |
| 検証: DB | Song は作成されていない |

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

#### 11-9. 名義の統一から曲登録正規化まで（#1008、#1029、#1137、#1230、#1290）

**テストファイル**: `tests/test_views.py`（`AuthorUnifyNameSetViewTest`、`AuthorUnifyNameConfirmViewTest`、`AuthorAliasesUnifyNameStatusTest`）、`tests/test_lib_author_helpers.py`

| 項目 | 内容 |
| --- | --- |
| 前提 | `Author(name="foo")` に別名 `foo_old`(`alias_type="past"`) が登録済み。`foo_old`という名前の別Authorは存在しない |
| 操作 | `GET /authors/<foo.id>/aliases/unify/confirm/` に `name="foo_old"` |
| 検証 | 統一内容の確認画面（対象Songの一覧＋「の作者が『foo_old』に統一されます」）が表示される |
| 操作 | 確認画面から `POST /authors/<foo.id>/aliases/unify` に `name="foo_old"` |
| 検証 | `Author.name`が`"foo_old"`に入れ替わり、旧名`"foo"`が新たな`past`別名として再登録される。`?toast=unify`付きで一覧画面へリダイレクト |
| 検証 | `History`に`history_type="edit"`のレコードが作成され、`send_discord()`が変更前後の名前を含む内容で呼ばれる |
| 操作（正規化の確認） | 上記の状態変更後、`POST /songs/new/` の`authors`に旧名`"foo"`を指定して曲登録 |
| 検証 | `get_or_create_authors()`が`"foo"`を`past`別名として解決し、新規Authorを作らず`Author(name="foo_old")`（同一のAuthor行）に紐づく。redirect先URLに`name_unified=1`が付与され、遷移先画面でinfoトーストが表示される |
| 操作（フォーム未変更での統一、#1137） | 以前の名称と同名の別Author（`Author(name="foo_old")`）がSongを持つ状態で、現在の名義のまま `POST /authors/<foo.id>/aliases/unify` に `name="foo"` |
| 検証 | 別AuthorのSongが全て`foo`に付け替わる。別Authorは削除されず曲数0で残る（#1137で削除を廃止） |
| 操作（統一の状態の表示、#1230） | 上記の統一の前後で `GET /authors/<foo.id>/aliases/` |
| 検証 | 統一前は「名義を統一する」の下に「名義が統一されていません」、統一後は「名義は統一されています」と表示される（統一するボタンが`unify_noop`になる条件と同じ） |
| 操作（既存Authorとの衝突ケース、#1029・#1137で仕様変更） | 選択したpast別名の名前と完全一致する別Authorが既に存在する状態で `POST /authors/<foo.id>/aliases/unify` に `name="foo_old"` |
| 検証 | かつては選択自体をブロックし（#1008）、次に衝突するAuthorを`foo`へ統合して削除していた（#1029）。#1137でAuthorの削除を廃止したため、`Author.name`のunique制約上`foo`を`foo_old`に変更できず、代わりに既存の`Author(name="foo_old")`を統一先とする。`foo`のSong・AuthorLink・AuthorAliasが統一先に付け替わり、旧名`"foo"`が統一先の`past`別名になる。`foo`は削除されず曲数0で残り、統一先の別名一覧へ`?toast=unify`付きでリダイレクトされる |
| 操作（旧名が別authorの別名と衝突するケース、#1290） | 別Author(`name="bar"`)が`foo`と同名の別名(`alias_type="another"`)を持つ状態で、`GET /authors/<foo.id>/aliases/unify/confirm/` に `name="foo_old"`（リダイレクトを辿る） |
| 検証 | 旧名`"foo"`を`foo_old`側の`past`別名として登録し直せない（別名の名前は全体でunique）ため、確認画面ではなく別名一覧(`?toast=unify_conflict&conflict=<bar.id>`)に移る。一覧には「別名の名前が重複しているため、名義を統一できませんでした。」のトーストと、`bar`の別名一覧へのリンクを含む理由(`#unify-name-conflict`)が表示される。`POST /authors/<foo.id>/aliases/unify`に直接送っても、`send_discord()`・DB・`History`に変更はなく同じ結果になる |

---

### 12. 作成結果の単語クリック入れ替えフロー（#1053）

**テストファイル**: `tests/test_views.py`（`AiViewTest` / `AiResultViewTest`）、`tests/test_api.py`（`WordCandidatesViewTest` / `AiWordSwapViewTest`）

単語クリック入れ替え機能は `ai/result/`（作成結果）にのみ提供する（方針転換により`ai/`＝最高評価の歌詞では提供しない）。`ai/result/`の表示（歌詞の単語分割・クリック可否の判定） → 候補取得API → 入れ替えPOSTによる新規`Ai`作成までの一連の流れを、HTTPリクエスト単位で連携させて検証する。ブラウザ側のクリック操作・ポップアップ表示（`word_swap.js`）自体はDjangoテストの対象外のため、実サーバー起動 + `curl`/Playwrightによる手動確認で代替した（本PR作成時に実施済み）。

#### 12-1. 表示から候補取得、入れ替え保存までの一連の流れ

| 項目 | 内容 |
| --- | --- |
| 前提 | `Ai(lyrics="私は走る", score=0, genetype="janome")`、`Word(word="走る", hinshi="動詞", candidate="駆ける")`が存在する |
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
| 前提 | `Ai(lyrics="私は走る", score=5, genetype="janome")`、`Word(word="走る", hinshi="動詞", candidate="駆ける")`が存在する |
| 操作 | `GET /ai/` |
| 検証 | Word候補が存在していても`class="word-token"`は含まれず、歌詞はプレーンテキストで表示される |

#### 12-4. 同じ入れ替え結果の重複防止

| 項目 | 内容 |
| --- | --- |
| 前提 | 12-1と同じ |
| 操作 | 同一の`base_id`・`token_index`・`candidate`で`POST /api/ai/swap/`を2回実行 |
| 検証 | 2回とも同じ`Ai`レコードのidが返り、新規レコードは1件しか作成されない |

---

### 13. ZAP診断に基づくセキュリティ対策フロー（#1126）

**テストファイル**: `tests/test_security.py`

ミドルウェア・テンプレート・JSが連携して、CSP・CORS・CSRFトークンの扱いが正しく機能することをHTTPリクエスト単位で検証する。ブラウザ上でCSP違反が発生しないこと・インラインハンドラから置き換えたイベントが動作することはDjangoテストの対象外のため、実サーバー起動 + Playwright（Chrome）で全ページの巡回と主要操作の確認を行った（本PR作成時に実施済み）。

#### 13-1. CSPとnonce

| 項目 | 内容 |
| --- | --- |
| 操作 | トップ・検索・曲・新規登録・編集・設定・歌詞作成・作成結果・お問い合わせ・宣伝・統計・記事一覧の各ページを`GET` |
| 検証1 | 全ページに`Content-Security-Policy`ヘッダーが付与される |
| 検証2 | `src`を持たないインラインの`<script>`（`json_script`のデータブロックを除く）に、ヘッダーと同じnonceが付与されている |
| 検証3 | 描画結果にインラインのイベントハンドラ属性（`onclick`等）が含まれない |
| 検証4 | APIのJSONレスポンス（`/api/song/<id>/?format=json`）にはCSPヘッダーが付与されない |

#### 13-2. インラインイベントハンドラの不使用

| 項目 | 内容 |
| --- | --- |
| 操作 | `subekashi`・`article`のテンプレート（`*.html`）と静的JS（`*.js`）を走査 |
| 検証 | 開始タグ内に`on〇〇=`形式のイベントハンドラ属性が含まれない（CSPで実行されないため） |

#### 13-3. CORS

| 項目 | 内容 |
| --- | --- |
| 操作1 | `Origin`ヘッダー付きで`GET /api/song/` |
| 検証1 | `Access-Control-Allow-Origin: *`が返り、`Access-Control-Allow-Credentials`は返らない |
| 操作2 | `Origin`・`Access-Control-Request-Method`付きで`OPTIONS /api/song/`（プリフライト） |
| 検証2 | HTTP 200、`Access-Control-Allow-Origin: *` |
| 操作3 | `Origin`ヘッダー付きでトップ・検索・曲ページを`GET` |
| 検証3 | CORSヘッダーが付与されない |

#### 13-4. CSRFトークン（csrftokenクッキーのHttpOnly化）

| 項目 | 内容 |
| --- | --- |
| 前提 | `Client(enforce_csrf_checks=True)` |
| 検証1 | `GET /songs/new/`で発行される`csrftoken`クッキーに`HttpOnly`が付く |
| 検証2 | `getCSRF()`を使うページ（トップ・検索・設定・作成結果）に`csrfmiddlewaretoken`が含まれる |
| 操作3 | `GET /setting/`で取得したトークンを`X-CSRFToken`に指定して`POST /api/setting/save/` |
| 検証3 | HTTP 200、設定のcookieが保存される |
| 操作4 | トークンなしで`POST /api/setting/save/` |
| 検証4 | HTTP 403 |
| 検証5 | `GET /ai/`のGETフォームに`csrfmiddlewaretoken`が含まれない（トークンがURLに含まれないこと） |

#### 13-5. サブリソース整合性（SRI）

| 項目 | 内容 |
| --- | --- |
| 操作 | `GET /` |
| 検証1 | Font Awesomeの`<link>`がjsDelivr（`cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@5.15.4/css/all.min.css`）を参照し、`integrity`と`crossorigin="anonymous"`が付与されている |
| 検証2 | CSPヘッダーの`style-src`・`font-src`に`https://cdn.jsdelivr.net`が含まれ、`https://use.fontawesome.com`が含まれない |

`use.fontawesome.com`は`Origin`ヘッダーがないリクエストにCORSヘッダーを返さず1年キャッシュさせるため、`crossorigin`なしで読み込んでいた頃のキャッシュが残るブラウザでアイコンが表示されなかった（#1215）。jsDelivrは常に`Access-Control-Allow-Origin: *`を返すため、読み込み元をjsDelivrに変更した。古いキャッシュがある状態での表示はDjangoテストでは検証できないため、Playwright（Chrome）で確認した。

---

### 14. 検索画面のフォームボタンの設定フロー（#1164）

**テストファイル**: `tests/test_views.py`（`SaveSettingsViewTest`）

#### 14-1. 設定画面で保存したフォームボタンの設定が検索画面に反映される

| 項目 | 内容 |
| --- | --- |
| 操作1 | `POST /api/setting/save/`で`form_button=icon`を保存し、`GET /songs/` |
| 検証1 | `#search-form-radios`に`icon-only`クラスが付く（`css/components/search_form.css`でラベルの丸と文字が非表示になる） |
| 操作2 | `POST /api/setting/save/`で`form_button=icon_text`を保存し、`GET /songs/` |
| 検証2 | `#search-form-radios`に`icon-only`クラスが付かない |

---

### 15. ページごとのOGP画像フロー（#1058）

**テストファイル**: `tests/test_views.py`（`OgpMetaTagTest`）

`base.html`のテンプレートタグ（`get_ogp_image_url`）が`metatitle`を署名したトークンで`og:image`のURLを作り、そのURLの`ogp_image`ビューがトークンを検証してPillowで画像を生成する流れを検証する。SNSで実際にカードが表示されるかはDjangoテストの対象外のため、デプロイ後にX・Discordで確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | 曲のページを`GET`し、`og:image`のURL（末尾に`?v={OGP_VERSION}`）から`ROOT_URL`を除いたパスを`GET` |
| 検証1 | HTTP 200、`Content-Type: image/png` |
| 操作2 | 曲・統計・編集者のページを`GET`し、`og:image`のURLのトークンを`load_ogp_token`で復元 |
| 検証2 | 各ページの`metatitle`（編集者のページは`Editor`のインスタンスを文字列にしたもの）に戻る |
| 操作3 | 存在しない曲・存在しないURLを`GET`（404.htmlを表示する） |
| 検証3 | OGPのタグ（`og:*`・`twitter:*`）が出ない |

---

### 16. レート制限フロー（#1187）

**テストファイル**: `tests/test_middleware.py`（`RatelimitMiddlewareClientTest`）

`@ratelimit(key='ip', rate='2/second', block=True)`のビューが送出した`Ratelimited`（`PermissionDenied`のサブクラス）を、Djangoが403のレスポンスにする前に`RatelimitMiddleware`の`process_exception`が429にし、外側の`CacheControlMiddleware`がpublicのキャッシュを付けないことを検証する。1秒の区切りをまたいでカウントがリセットされないよう、`django_ratelimit.core.time`をモックして時刻を固定する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | 同じ秒に`/api/html/song_cards`へ3回`GET` |
| 検証1 | 2回目まではHTTP 200、3回目はHTTP 429で、`{"error": "Rate limit exceeded"}`、`Retry-After: 1`、`Cache-Control: no-store` |
| 操作2 | 同じ秒に`/api/html/song_guessers?guesser=曲`へ3回`GET` |
| 検証2 | 検証1と同じ |
| 操作3 | 同じ秒に`/api/html/song_cards`へ3回`GET`した後、時刻を1秒進めて`GET` |
| 検証3 | HTTP 200 |

---

### 17. 管理画面での記事のタイトルのマークダウン変換フロー（#483）

**テストファイル**: `article/tests.py`（`ArticleAdminTest`）

管理画面のフォームが`Article.clean()`で変換後のタイトルの文字数を検証し、`Article.save()`でタイトルをHTMLに変換して保存する流れを検証する。変換でタグの分だけ文字数が増えても、フォームの`max_length`の検証は変換前の入力に対して行われるため、`clean()`で検証しないと保存時にDBのエラーになる。

| 項目 | 内容 |
| --- | --- |
| 前提 | スーパーユーザーでログインしている |
| 操作1 | `POST /admin/article/article/add/` `{title="**太字**", is_md="on", ...}` |
| 検証1 | 一覧へリダイレクト (302)、保存されたタイトルが`<strong>太字</strong>` |
| 操作2 | `POST /admin/article/article/add/` `{title="**a**"×100（500文字）, is_md="on", ...}` |
| 検証2 | HTTP 200で「HTMLに変換すると1800文字になり、上限の500文字を超えます。」と表示され、記事は作成されない |
| 操作3 | 操作1のあと`GET /admin/article/article/` |
| 検証3 | 一覧に`__str__`のタグを除いたタイトル`太字`が表示され、`&lt;strong&gt;`は表示されない |

---

### 18. トップ画面の検索の表示の設定フロー（#585）

**テストファイル**: `tests/test_views.py`（`SaveSettingsViewTest`）

#### 18-1. 設定画面で保存した検索の表示の設定がトップ画面に反映される

| 項目 | 内容 |
| --- | --- |
| 操作1 | `POST /api/setting/save/`で`is_shown_search=all`を保存し、`GET /` |
| 検証1 | 検索画面と同じフォーム（`#search-form-radios`）が表示される |
| 操作2 | `POST /api/setting/save/`で`is_shown_search=on`を保存し、`GET /` |
| 検証2 | キーワードのみのフォーム（`#keyword`）が表示され、`#search-form-radios`は無い |
| 操作3 | `POST /api/setting/save/`で`is_shown_search=off`を保存し、`GET /` |
| 検証3 | 検索フォーム（`#search-form`）が表示されない |

#### 18-2. トップ画面の「全て表示」の検索フォームから検索画面への遷移（Playwrightで確認）

送信時のURLクエリへの変換はJS（`top.js`）で行うため、Djangoテストではなく開発サーバーとPlaywrightで確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | `is_shown_search=all`でトップ画面を開き、歌詞・並び替え（再生回数/多い順）・未完成（のみ）・界隈曲（以外）・メディア（YouTube）を入力して検索 |
| 検証1 | `/songs/?lyrics=...&sort=-view&is_lack=True&songrange=xx&mediatypes=youtube`に遷移し、検索画面で同じ値が選択・入力される。入力中はフィルタのバッジと自動で適用されるフィルタの案内が検索画面と同じく表示される |
| 操作2 | 操作1の後にトップ画面を開き、キーワードのみ入力して検索 |
| 検証2 | 検索画面で保存された並び替え・界隈曲がトップ画面でも選択されており、URLクエリは`?keyword=...`のみで、検索画面でも同じ並び替え・界隈曲が選択される |
| 操作3 | 保存された界隈曲（以外）を「指定なし」に変更して検索 |
| 検証3 | URLクエリに`songrange=all`が含まれ、検索画面でも「指定なし」が選択される |
| 操作4 | 原曲ボタン・song guesserをクリック |
| 検証4 | 模倣の曲IDが入力されるのみで遷移せず、検索すると`?imitate=<曲ID>`に遷移する |
| 操作5 | 何も入力せずに検索 |
| 検証5 | URLクエリなしの`/songs/`に遷移する |
| 操作6 | `is_saved_select=off`で並び替え・界隈曲・ネタ曲のcookie（`-view`・`subeana`・`off`）がある状態で、トップ画面からキーワードのみ入力して検索した後、並び替え・界隈曲を変更して検索 |
| 検証6 | トップ画面・検索画面ともにcookieではなくデフォルト値（`-post_time`・`all`・`on`）が選択され、URLクエリは`?keyword=...`のみ。変更した場合は`sort`・`songrange`がURLクエリに含まれて検索画面で選択されるが、cookieは変わらない |
| 操作7 | `is_saved_select`がon・offそれぞれで、(a) 界隈曲を変更してから元に戻して検索、(b) 表示後に`search_sort`のcookieを変え、`restoreFormValuesFromCookies()`で選択を書き換えて（bfcacheから戻ったときと同じ）検索、(c) 検索画面で並び替えを変更してからブラウザバックでトップ画面に戻り、変更せずに検索 |
| 検証7 | いずれもトップ画面で選択されていた値と検索画面で選択される値が一致する。(a) はURLクエリに含まれない。(b) はonの場合のみ書き換わり、`sort`がURLクエリに含まれる。(c) は`never_cache`のためbfcacheを使わずに再読み込みされ、onの場合は検索画面で保存した値が選択される。トップ画面のレスポンスで`search_*`のcookieは保存されない |
| 共通 | コンソールにCSP違反・JSのエラーが出ない |

---

### 19. 曲ページのfull版・short版のリンクフロー（#667）

**テストファイル**: `tests/test_views.py`（`SongViewTest`）、`tests/test_lib_song_service.py`（`GetShortAndFullSongsTest`）、`tests/test_lib_author_helpers.py`（`GetSamePersonAuthorIdsTest`）

#### 19-1. 別名でつながっている名義の曲が曲ページに表示される

| 項目 | 内容 |
| --- | --- |
| 前提 | `Song(title="曲", author=foo)`・`Song(title="曲[short]", author=foo_sub)` が存在し、`foo`に別名`foo_sub`(`alias_type="another"`)を登録 |
| 操作1 | `GET /songs/<曲[short]のid>/` |
| 検証1 | song-infoの「full版」の行に`曲`へのリンクが表示される |
| 操作2 | `GET /songs/<曲のid>/` |
| 検証2 | song-infoの「short版」の行に`曲[short]`へのリンクが表示される |
| 操作3 | 別名の`alias_type`を`group`にして操作1・2 |
| 検証3 | 「full版」「short版」の行が表示されない |

#### 19-2. 曲ページの表示（Playwrightで確認）

| 項目 | 内容 |
| --- | --- |
| 操作 | full版の候補が複数ある曲・short版の曲・full版の曲の曲ページを開く |
| 検証 | song-infoに「full版」「short版」の行が候補の数だけ表示され、アイコンが表示される。リンクから相手の曲ページに遷移できる |
| 共通 | コンソールにCSP違反・JSのエラーが出ない |

---

### 20. APIでのニュースの登録フロー（#925）

**テストファイル**: `tests/test_api.py`（`NewsAPIViewTest`）

`X-API-Key`ヘッダー付きで`/api/news/`にPOSTしたニュースが、`Article.save()`でタイトルをHTMLに変換して保存され、`TopView`のニュースに表示される流れを検証する。

| 項目 | 内容 |
| --- | --- |
| 前提 | `API_KEY="test-api-key"` |
| 操作1 | `X-API-Key: test-api-key`で`POST /api/news/` `{"article_id": "testNews", "title": "[リンク](https://example.com)が公開される"}`のあと`GET /` |
| 検証1 | トップ画面のニュースに`<span><a href="https://example.com">リンク</a>が公開される</span>`が表示される |

---

### 21. 編集履歴の差分の表示フロー（#608）

**テストファイル**: `tests/test_views.py`（`SongHistoryViewTest`）、`tests/test_templatetags_changes.py`（`RenderChangesTest`）

保存するデータ（`History.changes`）は変えず、テンプレートタグで編集の変更履歴の表に`diff-table`クラスを付け、`editor.js`が`<details>`を開いたときに編集前と編集後のセルに差分を表示する。

#### 21-1. 編集の変更履歴の表

| 項目 | 内容 |
| --- | --- |
| 前提 | 曲に編集（見出しが`["種類", "編集前", "編集後"]`）と新規作成（見出しが`["種類", "内容"]`）のHistoryが存在 |
| 操作 | `GET /songs/<id>/history/` |
| 検証 | `<table class="diff-table">`が編集のHistoryの分だけ含まれ、`subekashi/js/editor.js`が読み込まれる |

#### 21-2. 差分の表示（Playwrightで確認）

差分はJS（`editor.js`）で求めるため、Djangoテストではなく開発サーバーとPlaywrightで確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | 曲の編集履歴（歌詞・URLの編集を含む）・編集履歴一覧を開く |
| 検証1 | 最初の`<details>`のみ差分が表示され、閉じている`<details>`には`<del>`・`<ins>`が無い（開いたときに求める） |
| 操作2 | 「全て開く/閉じる」を押す |
| 検証2 | 全ての編集の表に差分が表示される。行単位で比べ、似ている行（共通する文字が半分以上）どうしは文字単位で、それ以外は行全体が編集前は赤（`<del>`）、編集後は緑（`<ins>`）になる。空の行の削除・追加は`↵`で示す。編集前・編集後が空の場合はもう一方の全体が変更になる |
| 操作3 | 差分を表示したセルをクリックする |
| 検証3 | コピーされる文字列（セルの`innerText`）が差分を表示する前と同じ |
| 共通 | コンソールにCSP違反・JSのエラーが出ない |

---

### 22. すべあな界隈年表からの曲の登録・更新フロー（#52）

**テストファイル**: `tests/test_management_commands.py`（`TimelineCommandTest`）、`tests/test_lib_timeline_import.py`（`ImportTimelineTest`）

`timeline`コマンドが、すべあな界隈年表（Googleスプレッドシート）の2018年〜今年のシートを読み取り（`get_timeline`はモック化）、`import_timeline`で曲を新規作成・更新して、DB（Song・SongLink・History・Editor）に保存し、結果を出力する流れを検証する。スプレッドシートはAPIキーで読み取るのみで、書き換えるAPIは呼ばない（単体テスト計画書の26-2）。

#### 22-1. 新規作成から2回目の実行まで

| 項目 | 内容 |
| --- | --- |
| 前提 | `get_timeline`が、URLが登録されていない行を返す |
| 操作1 | `manage.py timeline --year 2018 2019` |
| 検証1 | 行ごとに曲が作られ、標準出力に「〇〇を新規作成（`<ROOT_URL>/songs/<id>`）」と「新規作成：3件、更新：0件、…」が出る |
| 操作2 | 同じ行でもう一度実行する（`ImportTimelineTest.test_second_run_changes_nothing`） |
| 検証2 | 曲もHistoryも増えない（毎日実行しても重複しない） |

#### 22-2. 既存の曲の更新

| 項目 | 内容 |
| --- | --- |
| 前提 | 行のURLが登録されている曲のカテゴリが年表と異なる |
| 操作 | `manage.py timeline --year 2018` |
| 検証 | 曲のカテゴリが年表の値になり、編集者id=1のHistoryが作られ、標準出力に「曲のカテゴリを編集（`<ROOT_URL>/songs/<id>`）」と「更新：1件」が出る |

#### 22-3. `--dry-run`

| 項目 | 内容 |
| --- | --- |
| 操作 | `manage.py timeline --year 2018 --dry-run` |
| 検証 | 結果は出力されるが、Song・SongLink・History・Editor・SongTimeline（#1269）は保存されない |

#### 22-4. 曲のページの「年表に登録する」「年表で見る」ボタン（#1269）

`TimelineCommandTest.test_song_page_opens_timeline_row`

| 項目 | 内容 |
| --- | --- |
| 前提 | `get_timeline`が、2018年のシート（`sheet_id=2018`）の5行目の、歌詞列が空の行を返す。`GOOGLE_SHEETS_SPREADSHEET_ID`を設定 |
| 操作1 | `manage.py timeline --year 2018` の後、作られた曲のページを`GET` |
| 検証1 | 「年表に登録する」ボタンのリンクが`https://docs.google.com/spreadsheets/d/<スプレッドシートのID>/edit#gid=2018&range=O5`（5行目の歌詞列のセルを選択した状態）で、コピーする曲のページのURL（`data-song-url`）が`<ROOT_URL>/songs/<id>/`。「年表で見る」は出ない |
| 操作2 | 歌詞列にその曲のページのURLを書いた行でもう一度実行し、曲のページを`GET` |
| 検証2 | 「年表で見る」ボタン（`#gid=2018&range=5:5`、5行目を選択した状態）が出て、「年表に登録する」は出ない |

---

### 23. トップ画面の投稿予定から検索画面への遷移フロー（#376）

**テストファイル**: `tests/test_views.py`（`UpcomingSongsFlowTest`）

トップ画面の「投稿予定」は、YouTubeの投稿日が未来の曲を投稿日の早い順に表示する。「もっと見る」は検索画面を投稿日/以降（今日の日付）・投稿日/早い順で開く。検索画面の投稿日の入力欄は日付のみのため、検索画面では今日の投稿済みの曲も表示される。リンクには`save_select=off`を付け、保存した並び替えを上書きしない。

#### 23-1. 「もっと見る」で今日以降に投稿（予定）の曲を検索する

| 項目 | 内容 |
| --- | --- |
| 前提 | YouTubeのURLが登録された、投稿日が昨日・今日の0時・明後日・明日の曲（作成順） |
| 操作1 | `GET /` |
| 検証1 | 投稿予定は明日・明後日の曲の順 |
| 操作2 | `is_saved_select=on`・`search_sort=-view`のcookieで、「もっと見る」のURL（`/songs/?upload_time_gte=<今日>&sort=upload_time&save_select=off`）を`GET` |
| 検証2 | 投稿日/以降の入力欄に今日の日付が入り、投稿日/早い順が選択される。`search_sort`のcookieは保存されない |
| 操作3 | 検索画面のフォームの値（`songs.js`の`formToQuery`）と同じ`GET /api/html/song_cards?upload_time_gte=<今日>&sort=upload_time&is_limited=False` |
| 検証3 | 今日・明日・明後日の曲の順に表示され、昨日の曲は表示されない |
| 操作4 | `GET /songs/` |
| 検証4 | 保存した並び替え（`-view`）が選択される |

---

### 24. トップ画面の初心者向け案内の表示フロー（#1236）

**テストファイル**: `tests/test_views.py`（`SaveSettingsViewTest`）

#### 24-1. 設定画面で保存した初心者向け案内の表示の設定がトップ画面に反映される

| 項目 | 内容 |
| --- | --- |
| 操作1 | `POST /api/setting/save/`で`is_shown_guide=off`を保存し、`GET /` |
| 検証1 | 初心者向け案内（`#guide`）が表示されない |
| 操作2 | `POST /api/setting/save/`で`is_shown_guide=on`を保存し、`GET /` |
| 検証2 | 初心者向け案内が表示される（閉じた案内を設定画面から再び表示できる） |

#### 24-2. 「表示しない」ボタンで閉じる（Playwrightで確認）

cookieの保存はJS（`top.js`）で行うため、Djangoテストではなく開発サーバーとPlaywrightで確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | cookieの無い状態でトップ画面を開き、背景の画像の下の「表示しない」ボタン（`#guide-close`）をクリック |
| 検証1 | 背景の画像とボタンを含む案内が消え、`is_shown_guide=off`のcookie（`path=/`・1年・`SameSite=Lax`）が保存される |
| 操作2 | トップ画面を開き直す |
| 検証2 | 案内が表示されない |
| 操作3 | 設定画面を開く |
| 検証3 | 「初心者向け案内の表示」で「非表示」が選択されており、「表示」に変更してトップ画面を開くと案内が表示される |
| 操作4 | 幅1280pxで、案内を表示した状態・検索の表示が「全て表示」の状態でトップ画面を開き、文字を入力する |
| 検証4 | 開いた時点ではスクロールせず（案内が画面の上にある）、検索の入力欄が選択されている。入力すると入力欄までスクロールし、入力欄に文字が入る。CSP違反・JSのエラーが出ない |
| 操作5 | 低速回線を想定し、`page.route`でフォント（`*.woff2`）の応答を5s遅らせた場合と、`top.js`の応答を4s遅らせた場合のそれぞれで、トップ画面を開いて説明文の不透明度を0.1sごとに記録する |
| 検証5 | フォントが遅い場合は、待つのを1sで打ち切って行に分け、フェードインする。`top.js`が遅い場合は、3s後のまとめての表示で表示され、行に分けて表示し直さない。どちらも、一度表示された文字が薄くならない |

---

### 25. フォントの設定フロー（#584）

**テストファイル**: `tests/test_views.py`（`SaveSettingsViewTest`）

#### 25-1. 設定画面で保存したフォントが全てのページに反映される

| 項目 | 内容 |
| --- | --- |
| 操作1 | cookieの無い状態で`GET /` |
| 検証1 | `<html lang="ja" data-font="imitate">`になる |
| 操作2 | `POST /api/setting/save/`で`font=k8x12s`を保存し、`GET /`・`GET /songs/`・`GET /setting/` |
| 検証2 | いずれも`data-font="k8x12s"`になる |
| 操作3 | `font`に不正な値（`"><script>alert(1)</script>`）のcookieを送信して`GET /` |
| 検証3 | `data-font="imitate"`になり、不正な値のスクリプトは出力されない |

#### 25-2. フォントの切り替えと読み込み（Playwrightで確認）

CSSの反映とフォントの読み込みはDjangoテストでは確認できないため、開発サーバーとPlaywrightで確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | cookieの無い状態でトップ画面を開き、読み込まれたフォント（`*.woff2`）を記録する |
| 検証1 | `html`・`input`・ヘッダーのロゴの`font-family`の先頭は`Imitate`で、`GenZenGothicKaiC.woff2`が読み込まれる |
| 操作2 | 設定画面の「フォント」を「k8x12S」に変更する |
| 検証2 | リロードせずに画面のフォントが切り替わり、`font=k8x12s`のcookieが保存される |
| 操作3 | 新しいブラウザ（コンテキスト）で、`font=k8x12s`のcookieを付けてトップ画面を開き、読み込まれたフォントを記録する |
| 検証3 | `html`・`input`・ヘッダーのロゴ・`.sansfont`（曲のカードのタイトル等）の`font-family`の先頭は`k8x12s`で、`GenZenGothicKaiC.woff2`は読み込まれず、`k8x12S.woff2`が読み込まれる。CSP違反・JSのエラーが出ない |
| 操作4 | cookieの無い状態（源全ゴシック）で、`.sansfont`の`font-family`の先頭と`font-weight`を調べる |
| 検証4 | `Noto Sans JP`・`1000`のままで、今までと変わらない |

---

### 26. 曲ページの埋め込みプレイヤーの表示と開閉の保存フロー（#1254）

**テストファイル**: `tests/test_views.py`（`SongViewTest`）、`tests/test_lib_embed.py`、`tests/test_lib_song_service.py`（`GetSongEmbedsTest`）、`tests/test_middleware.py`（`ContentSecurityPolicyMiddlewareTest`）

曲のURL（`SongLink`）から`lib/embed.py`で埋め込み用のURLを求め、ビュー・テンプレート・JS・CSPが連携して、歌詞の上のdetailsに埋め込みプレイヤーを表示する。開閉の状態は`is_shown_embed`のcookieに保存する。

#### 26-1. URLから埋め込みプレイヤーの表示まで

| 項目 | 内容 |
| --- | --- |
| 前提 | YouTube・ニコニコ動画・SoundCloudのURLと、X・BOOTHのURLを登録した曲 |
| 操作 | `GET /songs/<id>/` |
| 検証1 | `<details id="embed">`に、YouTube・ニコニコ動画・SoundCloudの3つの`<iframe>`だけがURLの順に出る（X・BOOTHは埋め込まない）。`src`はそれぞれ`youtube-nocookie.com`・`embed.nicovideo.jp`・`w.soundcloud.com`のもの |
| 検証2 | 模倣元・模倣曲のdetailsより後ろ、歌詞（`#lyrics-wrapper`）より前に表示する |
| 検証3 | CSPの`frame-src`に、3つの`src`のオリジンが含まれる |

#### 26-2. 開閉の保存と復元

| 項目 | 内容 |
| --- | --- |
| 操作1 | cookieの無い状態で`GET /songs/<id>/` |
| 検証1 | `<details id="embed" ... open>`で開いている |
| 操作2 | `is_shown_embed=off`のcookieを付けて`GET /songs/<id>/` |
| 検証2 | `open`が付かず閉じている。`on`・`OFF`・`<script>`のcookieでは開く |

#### 26-3. 開閉の保存と、各サービスのプレイヤーの表示（Playwrightで確認）

iframeの読み込み・CSP違反・cookieの保存はDjangoテストでは確認できないため、開発サーバーとPlaywright（Chrome）で確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | YouTube・ニコニコ動画・SoundCloud・ビリビリ動画・Google Drive・ScratchのURLがある実際の曲のページを開く |
| 検証1 | いずれもiframeが読み込まれてプレイヤーが表示され、CSP違反・JSのエラーが出ない。ニコニコ動画で削除済みの動画は、プレイヤーが「この動画は表示できません」と表示する（埋め込みの不具合ではない） |
| 操作2 | cookieの無い状態でページを開く |
| 検証2 | `is_shown_embed`のcookieは保存されない（初期の開いた状態では`toggle`のイベントで保存しない） |
| 操作3 | 「埋め込み」のsummaryをクリックして閉じ、リロードする |
| 検証3 | `is_shown_embed=off`（`path=/`・1年・`SameSite=Lax`）が保存され、リロード後も閉じている。閉じている間はiframeを読み込まない（`loading="lazy"`） |
| 操作4 | もう一度クリックして開き、リロードする |
| 検証4 | `is_shown_embed=on`が保存され、リロード後も開いていて、iframeを読み込む |
| 操作5 | 別の曲のページで閉じた後、ブラウザにキャッシュされた（`Cache-Control: max-age=1800`）最初の曲のページを開く |
| 検証5 | キャッシュされたHTMLが開いた状態でも、読み込み時にcookieの状態に合わせて開閉する |
| 操作6 | スマホの幅（375px）で開く |
| 検証6 | iframeが幅に収まり、横スクロールが出ない |
| 操作7 | SoundCloudの短縮URL（`on.soundcloud.com/…`）をプレーヤーに指定する |
| 検証7 | 「有効なSoundCloudのURLではない」と表示されるため、埋め込み対象にしない |

---

### 27. BANされた編集者の操作の制限フロー（#1281）

**テストファイル**: `tests/test_middleware.py`（`BannedEditorMiddlewareTest`）

`Editor.is_banned`がTrueの編集者が、ページの読み取り以外のリクエストをすると、`BannedEditorMiddleware`が各ビューの処理の前に止める。JSからのリクエスト（`/api/`、fetch・XHR）はJSONの403、ブラウザのフォーム送信は送信したフォームのあるページに`?toast=banned`を付けて戻し、`base.js`がトーストを表示する。戻れないときは500のページを表示する。管理サイトは止めない。

#### 27-1. 止められたリクエストが、DBにもDiscordにも何も残さない

| 項目 | 内容 |
| --- | --- |
| 前提 | `127.0.0.1`の`Editor`が`is_banned=True`。曲・削除済みの曲・作者・別名・`Ai`・`Ad`がある |
| 操作 | 曲の登録・編集・削除・削除の取り消し、別名の追加・編集・削除、名義の統一、お問い合わせ、宣伝のフォームのあるページを`Referer`にしてPOST。続けて`/api/`の単語の入れ替え・作成歌詞の評価・宣伝のクリック・設定の保存・公開の設定・ニュースの登録・曲の削除と作成・お問い合わせをPOST・PUT・PATCH・DELETE |
| 検証1 | フォームは`<Refererのパス>?toast=banned`への303、`/api/`はJSONの403（`{"detail": "処理を完了できませんでした。"}`）。どちらも曲・作者・別名・`Ai`・`Ad`・`History`・`Contact`・`SongLink`・`Editor`が変わらず、Discordに送信されない |
| 検証2 | ブラウザのフォーム送信（`Sec-Fetch-Mode: navigate`）を`Referer`なし、または他のサイト・管理サイトの`Referer`で行うと、500のページを表示する。fetch・XHRなど（`Sec-Fetch-Mode`が`navigate`以外、`X-Requested-With`、`Accept: application/json`、JSONの`Content-Type`）からフォームのURLにPOSTすると、リダイレクトせず（`Location`なし）JSONの403を返す |
| 検証3 | 同じIPのGET・HEADで、トップ・曲・登録・編集・別名一覧・お問い合わせ・宣伝が開ける。検索のPOST（`/songs/`）もできる |
| 検証4 | 同じIPで管理サイトにログインでき、編集者の変更画面で`is_banned`を外せる。`is_banned`を`False`にすると、曲の登録のPOSTが通り、曲が登録される |
| 検証5 | CSRFの検証を有効にしても、BANされた編集者のPOSTはトークンの有無にかかわらずBANとして止まる（CSRFの失敗にならない）。BANされていない編集者はトークンが必要なまま（トークン無しは403のCSRFの失敗、正しいトークンは302） |

#### 27-2. 戻したページでのトースト表示（Playwrightで確認）

トーストの表示とCSP違反はDjangoテストでは確認できないため、開発サーバーとPlaywright（Chrome）で確認する。

| 項目 | 内容 |
| --- | --- |
| 前提 | 開発DBのコピーで、自分の`Editor`を`is_banned=True`にする |
| 操作1 | 曲の登録・編集・削除、別名の追加・編集・削除、名義の統一、お問い合わせの送信ボタンを押す |
| 検証1 | いずれも元のページに戻り、「処理を完了できませんでした。」のトースト（文言は`<body data-banned-message>`から読む）が出る。URLから`toast=banned`が消え、CSP違反・JSのエラーが出ない |
| 操作2 | `Referer`付きで、フォームのURL（`/songs/new/`）に`fetch`でPOSTする |
| 検証2 | リダイレクトされず、403のJSON（`{"detail": "処理を完了できませんでした。"}`）が返り、`response.ok`が`false`になる |
| 操作3 | `rel="noreferrer"`を付けたフォームをブラウザで送信する（`Referer`が付かないフォーム送信） |
| 検証3 | 500のページ（「内部エラーが発生した為…」）が表示される |
| 操作4 | `/admin/login/`で管理者がログインする |
| 検証4 | BANされた編集者のIPでもログインでき、管理サイトの操作ができる |
| 操作5 | 曲の閲覧・検索条件の変更をする |
| 検証5 | 閲覧と検索はできる |

---

### 28. 編集者の荒らし報告フロー（#1291）

**テストファイル**: `tests/test_views.py`（`EditorViewTest`・`EditorReportViewTest`）、`tests/test_forms.py`（`EditorReportFormTest`）

編集者のページの「報告」ボタンから報告のフォームを開き、理由を送信すると、`CONTACT_DISCORD_URL`のDiscordに「理由・報告された編集者の管理画面のURL・報告した人の暗号化したIP」を送り、編集者のページに戻ってトーストを表示する。報告はDBに保存しない。

#### 28-1. 報告ボタンから報告の送信まで

| 項目 | 内容 |
| --- | --- |
| 前提 | 公開の編集者（他人）。`send_discord`はモック |
| 操作1 | `GET /editor/<id>/` |
| 検証1 | `.action-buttons`内に「報告」ボタン（`#editor-report`、`/editor/<id>/report/`へのリンク）がある。自分の編集者のページには無い。非公開の編集者のページには、履歴は出さず、報告ボタンだけがある |
| 操作2 | `GET /editor/<id>/report/`、続けて`POST /editor/<id>/report/` `{reason="..."}`（`X-Real-IP`付き） |
| 検証2 | フォームを表示し、POSTは`/editor/<id>/?toast=report`へリダイレクトする。`CONTACT_DISCORD_URL`宛に、理由・`ROOT_URL`+管理画面の編集者の編集画面・報告した人の`encrypt(X-Real-IP)`を含む文面を1回送る。`Editor`・`History`は増えない |
| 操作3 | `GET /editor/<id>/?toast=report` |
| 検証3 | 「報告しました。ご協力ありがとうございます。」のトーストを表示するスクリプトを含む |
| 操作4 | 報告理由が空・1000文字超・Discordに送信できない状態で`POST` |
| 検証4 | リダイレクトせずHTTP 200でエラーのトーストを表示し、入力した理由を残す。空・1000文字超ではDiscordに送らない |
| 操作5 | 自分の編集者・存在しない編集者に`GET`・`POST` |
| 検証5 | 自分の編集者は編集者のページへリダイレクト、存在しない編集者はHTTP 404。どちらもDiscordに送らない |

#### 28-2. 報告の画面とトースト（Playwrightで確認）

CSP違反・JSのエラー・トーストの表示はDjangoテストでは確認できないため、開発サーバーとPlaywright（Chrome）で確認する。

| 項目 | 内容 |
| --- | --- |
| 操作1 | 公開の編集者のページを開き、「報告」ボタンをクリックし、報告理由を入力して送信する（`SEND_DISCORD=False`のため実際には送らない） |
| 検証1 | ボタンは「再読み込み」「全て開く/閉じる」と同じ`.action-buttons`に並ぶ。報告のページは理由欄が必須で最大1000文字、CSRFトークンを含む。送信ボタンは理由が空・空白だけの間は無効（`disabled`の見た目）で、入力すると有効になる。送信後は編集者のページに戻って「報告しました。ご協力ありがとうございます。」のトーストを表示し、URLの`toast`クエリは消える。CSP違反・JSのエラーが出ない |
| 操作2 | 「戻る」リンクをクリックする |
| 検証2 | 編集者のページに戻る |
| 操作3 | 自分のIP（`X-Real-IP`）で、その編集者のページと報告のページを開く |
| 検証3 | 「(あなた)」と表示され、報告ボタンは無い。報告のページは編集者のページへリダイレクトする |
| 操作4 | スマホの幅（375px）で編集者のページと報告のページを開く |
| 検証4 | 横スクロールが出ない |

---

### 29. 非公開の編集者の履歴からの報告フロー（#1294）

**テストファイル**: `tests/test_views.py`（`HistoriesViewTest`・`SongHistoryViewTest`・`HistoryReportViewTest`）

非公開の編集者の履歴は「編集者: 非公開」とだけ表示され、編集者のページへリンクしないため、履歴ごとの「報告」リンクから報告のフォームを開く。編集者のIDが画面・URLに出ると、同じIDの履歴どうしが同じ非公開の編集者のものだと分かってしまうため、履歴のIDだけで報告し、サーバーで履歴から編集者を引く。送信後は、報告を始めたページ（`next`）へ戻ってトーストを表示する。

#### 29-1. 履歴の報告リンクから報告の送信まで

| 項目 | 内容 |
| --- | --- |
| 前提 | `is_open=False`の編集者の履歴。`send_discord`はモック |
| 操作1 | `GET /histories/?q=報告&page=1`、`GET /songs/<id>/history/` |
| 検証1 | 非公開の編集者の履歴だけに、`/histories/<履歴のid>/report/?next=<そのページ>`への「報告」リンクがある。公開・強制公開・自分の編集者の履歴にはリンクが無い。どちらのページも、編集者のIDを含まない |
| 操作2 | `GET /histories/<履歴のid>/report/?next=...`、続けて`POST`（`reason`と`next`、`X-Real-IP`付き） |
| 検証2 | フォームと、対象の編集（履歴のタイトル）を表示し、編集者のIDは出さない。POSTは`next`に`toast=report`を付けてリダイレクトする。`CONTACT_DISCORD_URL`宛に、理由・編集者の管理画面のURL・履歴の管理画面のURL・報告した人の`encrypt(X-Real-IP)`を含む文面を1回送る。`Editor`・`History`は増えない |
| 操作3 | `GET /histories/?toast=report`、`GET /songs/<id>/history/?toast=report` |
| 検証3 | 「報告しました。ご協力ありがとうございます。」のトーストを表示するスクリプトを含む |
| 操作4 | `next`を他のサイトのURL・`//`始まり・`javascript:`・空にして`POST` |
| 検証4 | 他のサイトなどへは飛ばさず、`/histories/?toast=report`へ戻す |
| 操作5 | 空・1000文字超の報告理由、Discordに送信できない状態、自分の履歴、存在しない履歴、BANされた編集者で`POST` |
| 検証5 | 理由の誤り・送信の失敗はHTTP 200でエラーを表示し、入力した理由と`next`を残す。自分の履歴は`next`へリダイレクト、存在しない履歴はHTTP 404、BANされた編集者は`?toast=banned`を付けて303。いずれもDiscordに送らない |

#### 29-2. 一覧から報告してトーストが出るまで（Playwrightで確認）

CSP違反・JSのエラー・トーストの表示はDjangoテストでは確認できないため、開発サーバー（専用DB）とPlaywright（Chrome）で確認する。

| 項目 | 内容 |
| --- | --- |
| 前提 | 非公開の編集者の履歴がある、開発DBのコピー。`SEND_DISCORD=False`のため実際には送らない |
| 操作1 | `/histories/`を開き、非公開の編集者の履歴を開いて、「報告」リンクをクリックし、報告理由を入力して送信する |
| 検証1 | 報告のページは「編集を報告」で、対象の編集（日時とタイトル）を表示し、送信ボタンは入力するまで無効。HTMLに編集者のIDを含まない。送信後は、元の一覧のページ（`?page=`を維持）へ戻って「報告しました。ご協力ありがとうございます。」のトーストを表示し、URLの`toast`は消える。CSP違反・JSのエラーが出ない |
| 操作2 | 同じ履歴を、曲の履歴（`/songs/<id>/history/`）から同様に報告する |
| 検証2 | 送信後は曲の履歴へ戻ってトーストを表示する |
| 操作3 | 自分のIP（`X-Real-IP`）で、曲の履歴と、自分の履歴の報告ページを開く |
| 検証3 | 「(あなた)」と表示され、「報告」リンクは無い。自分の履歴の報告ページは`next`へリダイレクトする |
| 操作4 | `next=https://evil.example/`で報告のページを開く。スマホの幅（375px）で報告のページと一覧を開く。存在しない履歴の報告のページを開く |
| 検証4 | 「戻る」リンクは`/histories/`。横スクロールが出ない。存在しない履歴はHTTP 404 |

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
3. **StaticFilesStorage**: `@override_settings(STORAGES={"default": {...}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})` で ManifestStaticFilesStorage を無効化（Django 5.2でSTATICFILES_STORAGE設定は廃止されたためSTORAGES形式を使用）
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
| **中** | 削除フロー (3) | 単体テストでほぼカバー済みだが、DB 書き込みの確認が必要 |
| **中** | 作者管理フロー (6) | get_or_create の重複防止は実 DB で確認が重要 |
| **中** | YouTube API 連携フロー (10) | 外部 API との連携は結合テストでしか確認できない |
| **低** | 模倣関係フロー (7) | M2M の操作は比較的単純 |
| **低** | 歌詞 CRLF 正規化フロー (8) | モデルのsave()で動作。既存モデルテストで一部カバー済み |
| **低** | 履歴フロー (9) | 表示確認のみ |
