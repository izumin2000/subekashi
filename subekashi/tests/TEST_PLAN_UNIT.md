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
| ライブのURL（#52） | `https://www.youtube.com/live/dQw4w9WgXcQ?feature=share`・`https://youtube.com/live/dQw4w9WgXcQ` | `True` |
| チャンネルのライブのページ・コミュニティ投稿（#52） | `https://www.youtube.com/@subekashi/live`・`https://www.youtube.com/post/...` | `False`（動画ではない） |
| 非YouTube URL | `https://nicovideo.jp/watch/sm12345` | `False` |
| 空文字列 | `""` | `False` |

#### 1-2. `get_youtube_id(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| youtu.be URL | `https://youtu.be/dQw4w9WgXcQ` | `"dQw4w9WgXcQ"` |
| ショートURL | `https://youtube.com/shorts/abcdefghijk` | `"abcdefghijk"` |
| ライブのURL（#52） | `https://www.youtube.com/live/dQw4w9WgXcQ?si=xxxx` | `"dQw4w9WgXcQ"` |
| 非YouTube URL | `https://example.com` | `"https://example.com"` (そのまま返す) |

#### 1-3. `format_youtube_url(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常YouTube URL | `https://www.youtube.com/watch?v=dQw4w9WgXcQ` | `"https://youtu.be/dQw4w9WgXcQ"` |
| 既に短縮済み | `https://youtu.be/dQw4w9WgXcQ` | `"https://youtu.be/dQw4w9WgXcQ"` |
| ライブのURL（#52） | `https://www.youtube.com/live/dQw4w9WgXcQ?feature=share` | `"https://youtu.be/dQw4w9WgXcQ"` |
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
| ライブのURL（#52） | `"https://www.youtube.com/live/dQw4w9WgXcQ?si=xxxx"` | `"https://youtu.be/dQw4w9WgXcQ"`（編集画面などで許可されているURLとして扱われる） |
| 複数URL | `"https://youtu.be/abc1234abcd,https://x.com/u/1"` | 各URLが正規化されたカンマ区切り |
| ビリビリ動画のURL（#1246） | `"https://www.bilibili.com/video/av417727107/,https://www.bilibili.com/video/BV1in4y1Q7qw/?p=2"` | `"https://bilibili.com/video/BV1qV411J7Kq,https://bilibili.com/video/BV1in4y1Q7qw?p=2"`（`format_bilibili_url` で揃える） |

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
| すべあな界隈年表にあるURLのドメイン（`clean_url`を通してから判定） | `https://bowlroll.net/file/284458`・`https://misskey.io/notes/...`・`https://booth.pm/ja/items/...`・`https://example.booth.pm/items/...`・`https://piapro.jp/t/WuJy`・`https://rechord.cc/...`・`https://www.dropbox.com/scl/fi/...?rlkey=...&dl=0` | それぞれ `bowlroll`・`misskey`・`booth`・`piapro`・`rechord`・`dropbox`（Issue #1247） |
| 追加したドメインのなりすまし | `https://bowlrollXnet.example.net/`・`https://xmisskey.io/`・`https://booth.pm.attacker.example/`・`https://piapro.jp.attacker.example/`・`https://xrechord.cc/`・`https://dropbox.com.attacker.example/` | `False`（Issue #1247） |
| Discordのメッセージのリンク | `https://discord.com/channels/111/222/333` | `False`（サーバーの参加者しか見られないため許可しない、Issue #1247） |

#### 1-7. `get_all_media(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 許可されているURL | `https://youtu.be/...`・`https://x.com/...`・`https://nicovideo.jp/...` | それぞれ `youtube`・`x`・`nicovideo`。`id`・`name`・`icon` を持つ |
| 追加したドメインのURL | `https://booth.pm/ja/items/5057223` | `booth`（「許可されていないURL」にならない、Issue #1247） |
| 許可されていないURL | `https://totally-unknown-domain-abc123.example.com/` | `disallow` |

#### 1-8. `convert_av_to_bv(aid)`（#1246）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| ビリビリ動画がBV番号を導入したときの例 | `170001` | `"BV17x411w7KC"` |
| すべあな界隈年表にBV番号で、DBにav番号で登録されていた動画 | `417727107` | `"BV1qV411J7Kq"` |
| av番号が2^30を超えた2024年以降の動画 | `111298867365120` | `"BV1L9Uoa9EUx"` |

#### 1-9. `format_bilibili_url(url)`（#1246）

ビリビリ動画の動画のURLを `https://bilibili.com/video/BV<id>` に揃える。`b23.tv` の短縮URLは、リダイレクト先を取得しないと動画が分からないため対象外。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| `www.`・末尾の`/`・クエリ | `https://www.bilibili.com/video/BV11ar4YcEyF/?spm_id_from=...&vd_source=...` | `"https://bilibili.com/video/BV11ar4YcEyF"` |
| 揃えたURL | `https://bilibili.com/video/BV11ar4YcEyF` | そのまま返す |
| スマホ版・http・フラグメント | `https://m.bilibili.com/video/BV11ar4YcEyF`・`http://bilibili.com/video/BV11ar4YcEyF#reply` | `"https://bilibili.com/video/BV11ar4YcEyF"` |
| av番号 | `https://www.bilibili.com/video/av417727107/` | `"https://bilibili.com/video/BV1qV411J7Kq"` |
| パートの指定 | `?p=1` / `?p=2` / `?p=3&vd_source=...` / av番号のURLの`?spm_id_from=...&p=02` / `?p=abc` | `p` を消す / `?p=2` / `?p=3` / BV番号のURLに`?p=2` / `p` を消す（1つの動画のパートごとに別の曲のことがあるため、2パート目以降のみ残す） |
| 動画のURLではない・動画IDが不正 | 桁数の多いBV番号（`BV1bcvtezEAcc`、年表にある誤記）・2^51以上のav番号・`/audio/au...`・`space.bilibili.com`・`bilibili.com.attacker.example`・ニコニコ動画のURL | そのまま返す |

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

#### 2-2. `validate_song_url(cleaned_url, exclude_song_id=None, allow_dup=False)`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 既存URLと重複する | SongLinkが既に存在し曲に紐付いている | エラーメッセージ文字列を返す |
| 重複しないURL | 新しいURL | `None` を返す |
| 自分自身を除外した場合 | `exclude_song_id` を指定し、同じ曲のURL | `None` を返す |
| `allow_dup=True` のSongLink | 重複URLだが `allow_dup=True` | `None` を返す |
| 引数`allow_dup=True`（#1285） | `allow_dup=False`のSongLinkが曲に紐付いているURLに、引数`allow_dup=True`を渡す | `None` を返す（重複を許可して保存するURLは、保存するときに許可するため重複をチェックしない）。SongLinkの`allow_dup`は変わらない |
| 引数`allow_dup=True`でもURLが長すぎる（#1285） | 引数`allow_dup=True`で、`len(url) == max_length + 1` | エラーメッセージ文字列を返す（長さは検証する） |
| 曲に紐付いていないSongLink | リンクは存在するが曲なし | `None` を返す |
| ユーザーが削除した曲だけに紐付くSongLink（#1239） | 紐付く曲が`is_removed=True`のみ | `None` を返す（登録されていないURLとして扱う） |
| 削除した曲と削除していない曲に紐付くSongLink（#1239） | `allow_dup=False`で、紐付く曲の一方が`is_removed=True` | エラーメッセージ文字列を返す（削除していない曲と重複する） |
| 上記のURLを別の曲の編集で登録（#1239） | 上記に加え、`exclude_song_id`に紐付いていない曲を指定 | エラーメッセージ文字列を返す |
| 上記のURLを紐付いている曲の編集で登録（#1239） | 上記に加え、`exclude_song_id`に削除していない方の曲を指定 | `None` を返す（自身のURLとして扱う） |
| URLが`SongLink.url`のmax_length丁度 (#1085) | `len(url) == max_length` | `None` を返す |
| URLが`SongLink.url`のmax_length超過 (#1085) | `len(url) == max_length + 1` | エラーメッセージ文字列を返す（MySQL移行時のData too long for column対策） |

#### 2-3. `create_song(fields)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な曲作成 | 有効な `SongFields` | Songオブジェクトが保存される |
| `post_time` が自動設定される | fields に `post_time` なし | `timezone.now()` に近い時刻が設定される |
| 各フラグが正しく設定される | `is_original=True`, `is_joke=False` など | Song属性がfieldsと一致する |
| `is_questionable` が正しく設定される | `is_questionable=True` | `song.is_questionable` が `True` |
| `category` が正しく設定される（#423） | `category="otomad"` | `song.category` が `"otomad"` |

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
| ユーザーが削除した曲に紐付くURLは残す（#1239） | URLが`is_removed=True`の曲にも紐付く | SongLinkは削除されず、削除した曲に紐付いたまま（復元に備える） |
| 削除した曲との模倣関係は残す（#1239） | 模倣元に`is_removed=True`の曲がある状態で、`imitate_songs`を空にして更新 | 削除した曲との模倣関係は消えない（編集画面に表示されないため） |
| 新しいURLの追加 | 新しいURL | SongLinkが作成・紐付けられる |
| 作者の更新 | 新しい author_objects | Song.authors が更新される |
| `is_questionable` の更新 | `is_questionable=True` | `song.is_questionable` が `True` に更新される |
| `category` の更新（#423） | `category="medley"` | `song.category` が `"medley"` に更新される |
| トランザクション失敗時のロールバック | DB エラーを模擬 | 変更が元に戻る |

#### 2-6. `build_delete_discord_text(song, reason, editor)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常なテキスト生成 | 曲オブジェクト、理由、編集者 | 曲ID・タイトル・作者・理由を含む文字列 |
| 先頭の形式（#1239） | 曲オブジェクト | 新規作成と同じく`削除されました`・曲のページのURL（`<ROOT_URL>/songs/<id>`）・空行で始まり、その後にタイトルが続く |

#### 2-6-1. `remove_song(song)`（#1239）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 曲を論理削除する | 曲オブジェクト | `is_removed=True`で保存され、`Song.objects`から取得できなくなる（`Song.all_objects`では取得できる） |
| 関連を残す | 作者・URL・模倣元のある曲 | 作者・URL・模倣元はそのまま残り、`SongLink.is_removed`も`False`のまま |
| 他のフィールドは保存しない | 保存前に`title`を書き換えた曲 | `is_removed`だけを保存し、`title`・`post_time`は変わらない |

#### 2-6-2. `restore_song(song)`（#1264）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 削除を取り消す | `remove_song`で削除した曲 | `is_removed=False`で保存され、`Song.objects`から再び取得できる |
| 関連が戻る | 作者・URL・模倣元のある曲 | 作者・URL・模倣元が削除前のまま戻り、作者の曲（`author.songs`）にも含まれる |
| 他のフィールドは保存しない | 保存前に`title`を書き換えた曲 | `is_removed`だけを保存し、`title`・`post_time`は変わらない |

#### 2-6-3. `get_restore_conflict_songs(song)`（#1264）

削除した曲のURLが削除していない他の曲に登録されていると、削除を取り消すとURLが重複するため取り消せない

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 削除した曲だけのURL | URLが削除した曲だけに紐付く | 空 |
| 他の曲に登録されたURL | URLが削除していない他の曲にも紐付く | その曲を返す |
| 他の削除した曲に登録されたURL | URLが`is_removed=True`の他の曲にも紐付く | 空（取り消しても重複しない） |
| 重複を許可したURL | `allow_dup=True`のURLが他の曲にも紐付く | 空 |
| 複数のURLが同じ曲に登録 | 2つのURLが同じ他の曲に紐付く | その曲を1回だけ返す |
| 他の曲だけのURL | 削除した曲と関係ないURLが他の曲に紐付く | 空 |

#### 2-6-4. `build_restore_discord_text(song, reason, editor)`（#1264、#1275）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 削除と同じ形式 | 作者のある曲、取り消しの理由、編集者 | `削除が取り消されました`・曲のページのURL・空行で始まり、タイトル・チャンネル名・`理由：<理由>`・編集者が続く |

#### 2-7. `build_edit_song_discord_text(song_id, song, fields, author_objects, cleaned_url, imitate_songs)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| タイトル変更 | before と after が異なるタイトル | 変更差分が `changes` リストに含まれる |
| 変更なし | before と after が同じ | `changed_labels` が空リスト |
| 複数フィールドの変更 | 複数の差分 | 全変更が `changes` に含まれ、`edit_title` に反映 |
| `is_questionable` の変更 | before/after で `is_questionable` が異なる | `changed_labels` に「界隈曲?」が含まれる |
| `category` の変更（#423） | `song` → `cover` | `changed_labels` に「カテゴリ」が含まれ、`changes` に `["カテゴリ", "曲", "カバー"]`（選択肢の表示名）が含まれる |
| `category` が同じ（#423） | before/after で `category` が同じ | `changed_labels` に「カテゴリ」が含まれない |

#### 2-8. `get_short_base_title(title)`（#667）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 角括弧の short | `"鏡[short]"`、`"鏡 [short]"` | `"鏡"`（直前の空白も除く） |
| 大文字を含む short | `"痕跡[Short]"`、`"濛（SHORT）"` | `"痕跡"`、`"濛"`（大文字小文字を区別しない） |
| short 以外の語を含む括弧 | `"00C(Short Ver.)"`、`"夜雨[very short]"`、`"無常【short】"` | 括弧ごと除いたタイトル |
| short の後ろに注記がある | `"微細構造[short] (旧:▇)"`、`"#40 [short] [Demo]"` | `"微細構造"`、`"#40"`（short の部分以降を除く） |
| 括弧のない short | `"NNN - short ver."`、`"死んだらしいshort"`、`"炭酸 short. (off vocal)"` | `"NNN"`、`"死んだらしい"`、`"炭酸"` |
| short が2か所にある | `"目 short.(旧:👁 short.)"` | `"目"`（最初の short で切る） |
| タイトルが short だけ | `"short"`、`"[short]"` | `""` |
| short 版でない | `"鏡"`、`"relix[full]"` | `None` |

#### 2-9. `get_full_base_title(title)`（#667）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 末尾の full の括弧 | `"relix[full]"`、`"ʓ [Full]"`、`"チェーン（Full）"`、`"///[FULL]"`、`"曲 (Full ver.)"` | 括弧ごと除いたタイトル |
| 末尾の full の語 | `"死んだらしいfull"`、`"淫夢グミ　FULLスギ"` | `"死んだらしい"`、`"淫夢グミ"` |
| 英単語の一部の full | `"Beautiful"` | そのまま |
| 末尾でない full | `"Full Moon"` | そのまま |
| full を含まない | `" 鏡 "` | 前後の空白を除いた `"鏡"` |

#### 2-10. `get_short_and_full_songs(song)`（#667）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| short 版の曲 | 同じ名義の `"鏡"` と `"鏡[short]"` | `"鏡[short]"` に対して `([鏡], [])` |
| full 版の曲 | 同じ名義の `"鏡"` と `"鏡[short]"` | `"鏡"` に対して `([], [鏡[short]])` |
| full 版の候補が複数 | 同じ名義の `"≡"` が2曲 | 2曲とも返す |
| short 版の候補が複数 | `"鏡[short]"` と `"鏡(very short)"` | 2曲とも返す |
| 名義が違う | 別の名義の `"鏡"` | リンクしない |
| 別名でつながっている名義 | `alias_type="another"` で直接つながっている名義の `"鏡"` | 双方向にリンクする |
| グループの別名 | `alias_type="group"` でつながっている名義の `"鏡"` | リンクしない |
| 作者のうち1人が一致 | short 版の作者が2人で、うち1人が full 版の作者 | リンクする |
| full 版に full が付いている | `"relix[full]"` と `"relix[short]"` | 双方向にリンクする |
| 英字の大文字小文字の違い | `"00c"` と `"00C(Short Ver.)"` | 双方向にリンクする |
| 英字以外の大文字小文字の違い | `"λ"`・`"Λ"` と `"Λ [short]"` | `"Λ"` のみ返す |
| 全角・半角の違い | `"-"` と `"﹣[short]"` | リンクしない |
| 記号の数が違う | `"⬚"` と `"⬚⬚[short]"` | リンクしない |
| short 版どうし | `"鏡[very short]"` と `"鏡[short]"` | リンクしない |
| タイトルが short だけ | `""` と `"short"` | リンクしない |
| 関係する曲がない | `"鏡"` のみ | `([], [])` |
| 作者がいない | 作者が未設定の `"鏡"` と `"鏡[short]"` | `([], [])` |

#### 2-11. `category_label(category)`（#423）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 選択肢にあるカテゴリ | `"arrange"` | `"アレンジ"`（`Song.CHOICES` の表示名） |
| 選択肢にないカテゴリ | `"unknown"` | `"unknown"`（そのまま返す） |

#### 2-12. `build_new_song_discord_text(song_id, fields, authors, cleaned_url, editor)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 戻り値 | 有効な `SongFields` | `changes`（リスト）とDiscordのテキスト（文字列）を返す |
| `changes` の見出し | 有効な `SongFields` | `changes[0] == ["種類", "内容"]` |
| タイトル・作者 | タイトルと作者 | テキストにタイトル・作者名が含まれる |
| `is_questionable=True` | `is_questionable=True` | テキストに「界隈曲?」が含まれる |
| カテゴリ（#423） | `category="medley"` | `changes` に `["カテゴリ", "メドレー"]`、テキストに `**カテゴリ**：`メドレー`` が含まれる（選択肢の表示名） |

#### 2-13. `split_songs_by_category(songs)`（#423）

曲ページの模倣元・模倣曲の一覧で、ネタ曲と曲以外のカテゴリの曲をdetailsにまとめるために使う。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 曲・ネタ曲・カテゴリごとに分ける | カテゴリが曲の曲・ネタ曲、カバー1曲・アレンジ2曲 | `songs` に曲、`joke_songs` にネタ曲、`category_groups` にアレンジ（2曲）・カバーの順（`SONG_CATEGORIES` の順）で入る |
| 曲以外のカテゴリのネタ曲 | `category="meme"`, `is_joke=True` | `joke_songs` ではなく、ネタ動画の `category_groups` に入る |
| 選択肢にないカテゴリ | `category="joke"`（変更前の値） | `songs` に入り、`category_groups` は空 |
| 曲がない | 空のQuerySet | すべて空 |

#### 2-14. `get_song_embeds(links)`（#1254）

曲ページの歌詞の上の埋め込みプレイヤーのために、`get_song_links_with_media(song)`のリンクのうち埋め込めるものを選ぶ。埋め込み用のURLと形は`lib/embed.py`の`get_embed()`（28章）で求める。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 埋め込めるリンク | YouTubeとニコニコ動画のURLがある曲 | `src`・`shape`（`get_embed()`の戻り値）と、リンクのサービス名（`name`。「YouTube」「ニコニコ動画」）を持つdictのリストを返す |
| 埋め込めないリンク | X・BOOTHのURLとYouTubeのURLがある曲 | YouTubeだけを返す |
| 同じ埋め込み | 同じ動画の`youtu.be`のURLと`youtube.com/watch?v=`のURL | 1件にまとめる |
| 順番 | ニコニコ動画・YouTubeの順のリンク | リンクの順に並ぶ |
| リンクがない | 空のリスト | 空のリスト |

#### 2-15. `allow_song_url_dup(url, ip, exclude_song_id=None)`（#1282）

URLの重複を許可（`SongLink.allow_dup = True`）し、そのURLを元から持つ曲の編集履歴に残す。編集者は`ip`から決める。`exclude_song_id`には保存する曲（編集している曲）を渡す（#1285）。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 重複を許可する | 曲に紐付く`allow_dup=False`のSongLink | `allow_dup=True`になり、そのSongLinkを返す |
| 曲の編集履歴に残す | 同上 | その曲に`history_type="edit"`のHistoryが1件でき、タイトルは「<曲名>のURLの重複を許可」、`changes`は`[["種類", "内容"], ["重複許可したURL", <URL>]]`、編集者は`ip`のEditor |
| 複数の曲に紐付く | SongLinkが2曲に紐付く | 2曲それぞれにHistoryが1件ずつできる |
| 削除した曲（#1239） | SongLinkに`is_removed=True`の曲も紐付く | 削除した曲にはHistoryを作らない |
| 紐付いていない曲 | 無関係な曲がある | その曲にはHistoryを作らない |
| 大文字小文字の違うURL | `url`が大文字小文字だけ違う | 同じSongLinkの重複を許可し、Historyも1件できる |
| 既に重複を許可したURL | `allow_dup=True`のSongLink | SongLinkを返すが、HistoryもEditorも作らない（ページを再読み込みしても履歴が増えない） |
| 2回呼ぶ | 異なる`ip`で続けて2回 | Historyは1件だけ |
| 同時に呼ぶ | 別々のDB接続から同時に2回。1つ目が`allow_dup=True`に更新してコミットする前に止め、その間に2つ目を呼ぶ（`TransactionTestCase`。SQLiteは行のロックを待たないため実行しない） | 2つ目はSongLinkの行のロックを待ち、1つ目のコミット後は更新できず、Editorも作らない。Historyは1件だけ |
| 登録されていないURL | SongLinkが存在しない | `None`を返し、HistoryもEditorも作らない |
| 曲に紐付いていないSongLink | リンクは存在するが曲なし | `allow_dup=True`にするが、Historyは作らない |
| 保存する曲にしか紐付いていないURL（#1285） | `exclude_song_id`に、SongLinkにだけ紐付いている曲を指定 | `None`を返し、`allow_dup=False`のまま、HistoryもEditorも作らない（重複していないURLは許可しない） |
| 保存する曲にも別の曲にも紐付いているURL（#1285） | `exclude_song_id`に、SongLinkに紐付いている曲の1つを指定。SongLinkはもう1曲にも紐付く | `allow_dup=True`になり、Historyは`exclude_song_id`の曲以外の曲にだけ作る |
| 保存する曲が紐付いていないURL（#1285） | `exclude_song_id`に、SongLinkに紐付いていない曲を指定 | `allow_dup=True`になり、SongLinkに紐付く曲にHistoryが1件でき、`exclude_song_id`の曲にはできない |
| 外側のトランザクションが失敗する（#1285） | `transaction.atomic()`の中で呼んだ後、例外を送出する | `allow_dup=False`のまま、HistoryもEditorも作らない（曲の保存と同じトランザクションで呼べば、保存できなかったときに重複を許可したままにしない） |

#### 2-15-2. `build_allow_dup_discord_text(link, ip)`（#1285）

URLの重複を許可したことを知らせるDiscordテキストを作る。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| テキストの内容 | SongLinkと`ip` | 「重複許可したURL：」で始まり、URL・`{ROOT_URL}/songs/?url=<URL>`・`{ROOT_URL}/admin/subekashi/songlink/<id>`・`IP：<ip>`を含む |

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
| カテゴリが曲以外で歌詞なしの曲（#423） | `category="arrange"`, `is_inst=False`, `lyrics=""`, URLあり, `is_original=True` | 結果に含まれない（歌詞なし条件は `category="song"` が必須。歌詞を入力するのは曲の場合のみ） |
| ユーザーが削除した曲だけを模倣する曲（#1239） | 模倣元が`is_removed=True`の曲のみ、URL・歌詞あり | 結果に含まれる（削除した曲は模倣元として数えない）。`exclude()`の結果には含まれない |
| 削除した曲と削除していない曲を模倣する曲（#1239） | 模倣元の一方が`is_removed=True`、URL・歌詞あり | 結果に含まれない。`exclude()`の結果に含まれる |

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
| `bowlroll`・`misskey`・`booth`・`piapro`・`rechord`・`dropbox`（DB REGEXP経由の確認） | それぞれのメディアのURL（boothはショップのサブドメイン）のSongLinkが紐付いている曲 | 結果に含まれる。YouTube曲は含まれない（Issue #1247） |

#### 3-3-1. `filter_by_categorys(categorys)`（#423）

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 1つ指定 | `"arrange"` | カテゴリがアレンジの曲のみ含まれる |
| 複数指定（カンマ区切り） | `"song,meme"` | カテゴリが曲・ネタ動画の曲が含まれる |
| 存在しないカテゴリ | `"joke"` | 結果が空 |
| 「以外」の指定（先頭に~） | `"~song,~meme"` | カテゴリが曲・ネタ動画の曲を除き、アレンジの曲のみ含まれる |
| 「のみ」と「以外」の両方 | `"song,arrange,~arrange"` | 「のみ」のカテゴリのうち「以外」でない、カテゴリが曲の曲のみ含まれる |

#### 3-3-2. `split_categorys(categorys)`（#423）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 「のみ」と「以外」に分ける | `"arrange,~meme,cover,~song"` | `(["arrange", "cover"], ["meme", "song"])`（「以外」は先頭の~を除く） |
| 空の値 | `""`・`"arrange,,~meme"` | 空の値は無視する（`([], [])`・`(["arrange"], ["meme"])`） |

#### 3-4. `make_is_lack_annotation()`

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 未完成の曲に annotate | 上記の `filter_by_lack` と同じ条件 | `is_lack=True` がアノテートされる |
| 完成した曲に annotate | URLと歌詞が揃っている曲 | `is_lack=False` がアノテートされる |
| `is_subeana=True` かつ特殊作者(id=1)なしの曲に annotate | `is_original=False`, `is_subeana=True`, `imitates`なし, 特殊作者(id=1)の紐付けなし | `is_lack=True` がアノテートされる |
| 特殊作者(id=1)が紐づいている曲に annotate | 上記に加え特殊作者(id=1)を紐付け | `is_lack=False` がアノテートされる |
| `is_questionable=True` かつURLなし・削除されていない曲に annotate | `is_questionable=True`, SongLink なし | `is_lack=True` がアノテートされる（URLなし条件は `is_questionable` を問わない） |
| `is_questionable=True` かつ歌詞なし等の曲に annotate | `is_questionable=True`, URLあり、歌詞なし等 | `is_lack=False` がアノテートされる（歌詞なし条件は `is_questionable=False` が必須） |
| カテゴリが曲以外で歌詞なしの曲に annotate（#423） | `category="notice"`, URLあり、歌詞なし | `is_lack=False` がアノテートされる（歌詞なし条件は `category="song"` が必須） |
| ユーザーが削除した曲だけを模倣する曲に annotate（#1239） | 模倣元が`is_removed=True`の曲のみ、URL・歌詞あり | `is_lack=True` がアノテートされる（`filter_by_lack()`と同じ判定） |

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

`YOUTUBE_FILTERS`・`YOUTUBE_SORTS` は `SongFilter.qs()` と曲の検索フォーム（search_form.js）の案内表示で共通して使用する。

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

#### 5-2. `get_same_person_author_ids(authors)`（#667）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 別名がない | 作者A | 作者Aのidのみ |
| 作者が空 | `[]` | 空の集合 |
| 正方向の別名 | 作者Aが別名「作者B」（`another`）を持つ | 作者A・作者Bのid |
| 逆方向の別名 | 作者Bが別名「作者A」（`past`）を持つ | 作者A・作者Bのid |
| グループの別名 | `alias_type="group"` でつながっている | 作者Aのidのみ |
| 別名に対応する作者がいない | 別名「存在しない作者」 | 作者Aのidのみ |
| 別名の別名 | 作者A→作者B→作者C | 作者Cは含まない（直接つながっている作者のみ） |
| 複数の作者 | 作者A・作者B | 両方のid |

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
| 全ての種類 | `category`が「不具合の報告」「提案」「質問」「その他」 | いずれも `is_valid() == True`（#1239で追加した「削除の取り消し」は、曲のページのボタンで取り消すようにしたため削除した。#1264） |
| detailが10000文字丁度 (#1085) | `detail="あ" * 10000` | `is_valid() == True` |
| detailが10000文字超 (#1085) | `detail="あ" * 10001` | `is_valid() == False` |

#### 6-2. `SongDeleteForm`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な入力 | `reason="削除理由の詳細"` | `is_valid() == True` |
| reasonが空 | `reason=""` | `is_valid() == False`、`"削除理由を入力してください。"` |

#### 6-2-1. `EditorReportForm`（#1291）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正常な入力 | `reason="他の曲のタイトルを繰り返し書き換えています"` | `is_valid() == True` |
| reasonが空 | `reason=""` | `is_valid() == False`、`"報告理由を入力してください。"` |
| reasonが空白のみ | `reason=" \n　"` | `is_valid() == False`、`"報告理由を入力してください。"` |
| reasonが1000文字丁度 | `reason="あ" * 1000` | `is_valid() == True` |
| reasonが1000文字超 | `reason="あ" * 1001` | `is_valid() == False`、`"報告理由は1000文字以内で入力してください。"`（Discordは2000文字ごとに分割して1秒待つため、長い報告で処理を遅くできないようにする） |

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
| categoryは任意（#423） | `category` 省略 | `is_valid() == True`、`cleaned_data["category"] == ""`（ビューで編集前のカテゴリのままにする） |
| 正しいcategory（#423） | `category="arrange"` | `cleaned_data["category"] == "arrange"` |
| 不正なcategory（#423） | `category="joke"`（変更前の値） | `is_valid() == False`、`"カテゴリが不正です。"` |

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
| 曲を削除した後のトースト（#1239） | `?toast=delete` | `showToast("ok", "曲を削除しました。");`が含まれる。`toast`が無ければ含まれない |
| 通知に失敗した削除の後のトースト（#1239） | `?toast=delete_notify_error` | `showToast("warning", "曲を削除しましたが、管理者への通知に失敗しました。");`が含まれる |
| ニュース欄のリンク付与（#961） | `tag="news"`, `handle_as_news=False`の記事 | タイトルのみ表示され`<a>`タグは付与されない |
| ニュース欄のリンク付与（#961） | `tag="release"`の記事 | `DefaultArticleView`へのURLでタイトル全体が`<a>`タグにくくられる |
| ニュース欄のリンク付与（#961） | `handle_as_news=True`の記事（`tag`は`news`以外） | `DefaultArticleView`へのURLでタイトル全体が`<a>`タグにくくられる |
| ニュース欄のリンク付与（#961） | `tag="news"`かつ`handle_as_news=True`の記事 | `handle_as_news`が優先され、リンクが付与される |
| タイトル中のリンクの除去（#483） | `tag="release"`でタイトルが`[リンク](https://example.com)と**太字**` | `<a>`が入れ子にならないよう、タイトル中のリンクだけ外して`<a href='（記事のURL）'>リンクと<strong>太字</strong></a>`になる |
| タイトル中のリンクの保持（#483） | `tag="news"`, `handle_as_news=False`でタイトルにリンクを含む | リンクでくくらないため、タイトル中のリンクはそのまま表示される |
| ニュースの切り替えボタン（#1116） | `news_type`クッキーなし（1つずつ表示） | `#single-news-display`と、`top.js`で切り替えのボタンを入れる`#single-news-dots`が置かれる |
| ニュースの切り替えボタン（#1116） | `news_type="all"`（一度に全て表示） | `#all-news-display`が置かれ、`#single-news-dots`は置かれない |
| 作成された歌詞の表示 | `genetype="janome", score=5`のAiレコードが存在 | 「作成された歌詞」欄に表示される |
| レガシーgenetype="model"は対象外（GPTインポート廃止） | `genetype="model", score=5`のレコードが存在 | 「作成された歌詞」欄に表示されない（`get_top_scored()`も`genetype="janome"`のみ対象） |
| PC向けグローバルヘッダーの配置（#1123） | `pc_menu_position`クッキーなし（トップ） | `#pc-global-header`が`#pc-header-menu`の中に1つだけ置かれる |
| PC向けグローバルヘッダーの配置（#1123） | `pc_menu_position=aside`（サイド） | `#pc-header-menu`は無く、`#pc-global-header`が`#subekashi-header`より前に1つだけ置かれる |
| フッターのプライバシーポリシーのリンク（#1170） | GETリクエスト | PCのフッター（`#footer-wrapper`）とスマホメニューのフッター（`#sp-menu-footer`）のそれぞれに、記事`privacy`（`/articles/privacy/`）へのリンクがある。記事は管理画面から作成するため、記事があるかは確認しない |
| 投稿予定の表示（#376） | 投稿日が3日後・1日後・1日前・無しの曲 | 「投稿予定」の見出しが表示され、context["upcomingInsL"]は投稿日が未来の曲のみで、投稿日の早い順（1日後・3日後） |
| 投稿予定が無い（#376） | 投稿日が過去の曲のみ | 「投稿予定」の見出しが表示されない |
| 投稿予定の曲数（#376） | 投稿日が未来の曲が11曲あり、`is_shown_upcoming`が無し・`5`・`10`・`15`・`0` | 5・5・10・11曲表示される。`0`（非表示）の場合はcontextに`upcomingInsL`が無く、見出しも表示されない |
| 投稿予定の設定のcookieの不正な値（#376） | `is_shown_upcoming`が`3`・`abc`・`<script>` | HTTP 200で、デフォルトの5曲表示される |
| 投稿予定の界隈曲・ネタ曲の表示設定（#376） | 投稿日が未来の界隈曲・界隈曲以外・ネタ曲 | cookie無し（`songrange=subeana`・`jokerange=off`）では界隈曲のみ、`songrange=all`・`jokerange=on`では3曲とも表示される（新着・未完成と同じく`Song.get_for_range`を使う） |
| 投稿予定に削除した曲を出さない（#376） | 投稿日が未来の削除した曲（`is_removed=True`、#1239）のみ | 「投稿予定」の見出しが表示されない |
| 投稿予定の「もっと見る」（#376） | 投稿日が未来の曲 | `/songs/?upload_time_gte=<今日の日付>&sort=upload_time&save_select=off`へのリンクがある。検索画面の投稿日の入力欄は日付のみのため、今日以降に投稿（予定）の曲を投稿日の早い順で検索し、保存した並び替えは上書きしない |
| viewportのmetaタグ（#1058） | GETリクエスト | `<meta name="viewport" content="width=device-width,...">`が含まれ、余分な`meta=""`属性が無い |
| 検索の表示のデフォルト（#585） | `is_shown_search`クッキーなし | context["is_shown_search"] = "on"、キーワードのみの検索フォーム（`#keyword`、placeholderは「タイトル・チャンネル名・歌詞・URL」）が表示され、`#search-form-radios`・`search_form.js`は無い |
| 検索の表示がキーワードのみ（#585） | `is_shown_search=on` | キーワードのみの検索フォームが表示され、`#search-forms`は無い |
| 検索の表示が非表示（#585） | `is_shown_search=off` | 「検索」の見出しと`#search-form`が無く、`search_form.js`も読み込まれない |
| 検索の表示が全て表示（#585） | `is_shown_search=all` | `#search-form`の中に検索画面と同じフォーム（`components/search_form.html`）が表示される。ラジオボタンの並びは`SEARCH_FORM_QUERIES`のキーと一致し、キーワードのラジオボタンのみ選択され、キーワードのフォームのみ`hidden`が無い。`#search-form-radios-toggle`・`#youtube-queries`・送信ボタン（`#searchsubmit`）を含む |
| 全て表示のJSの読み込み順（#585） | `is_shown_search=all` | `search_form.js`が`top.js`より先に読み込まれる |
| top.jsに渡す全て表示の判定（#585） | `is_shown_search`が`all`・`on`・`off`・不正な値 | インラインのスクリプトの`const isShownAllSearch`は`all`の場合のみ`true`で、`search_form.js`は`true`の場合のみ読み込まれる（ずれると`top.js`がReferenceErrorになるため） |
| 検索フォームのCSSの読み込み（#585） | `is_shown_search`が`all`・`on`・`off` | `css/components/search_form.css`は`all`の場合のみ、`top.css`より先に読み込まれる |
| 全て表示のフォームにCSRFトークンを含めない（#585） | `is_shown_search=all` | GETで送信するため、`#search-form`の中に`csrfmiddlewaretoken`が無い |
| 全て表示で保存したカテゴリを反映（#423） | `is_shown_search=all`, `is_saved_select=on`, `search_categorys=arrange,~meme` | 検索画面と同じく、アレンジの「のみ」・ネタ動画の「以外」のラジオボタンが選択される |
| 全て表示で検索の選択肢の保存を反映（#585） | `is_shown_search=all`, `is_saved_select=on`, `search_sort=-view`, `search_songrange=subeana`, `search_jokerange=off`, `form_button=icon` | 検索画面と同じく`-view`・`subeana`・`off`のラジオボタンが選択され、`#search-form-radios`に`icon-only`が付く |
| 全て表示で検索の選択肢の保存がoff（#585） | `is_shown_search=all`, `is_saved_select=off`, `search_sort=-view`, `search_songrange=subeana` | 保存された値ではなくデフォルト値（`-post_time`・`all`）のラジオボタンが選択される |
| 全て表示の初期の選択が検索画面と一致する（#585） | `is_shown_search=all`で、cookieなし・`is_saved_select=on`と保存された選択肢・`is_saved_select=off`と保存された選択肢・`is_saved_select=on`と不正な値の4通り | トップ画面と、URLクエリが無い検索画面で、選択されているラジオボタン（並び替え・界隈曲・ネタ曲・真偽値のフィルタの11個）が一致する（`top.js`は表示時から変更していないラジオボタンをURLクエリに含めないため） |
| 検索の表示設定のcookieの不正な値（#585） | `is_shown_search`が`keyword`・`ALL`・`<script>` | context["is_shown_search"] = "on"、キーワードのみの検索フォームが表示され、`search_form.js`・`search_form.css`は読み込まれない |
| 全て表示はトップ画面のURLクエリを使わない（#585） | `is_shown_search=all`, `is_saved_select=on`, `/?sort=-view&songrange=xx&is_lack=True&mediatypes=youtube`と`TEXT_FORMS`の全ての入力欄の値 | context["search_form"] = "keyword"、`-post_time`と未完成の「指定なし」が選択され、メディアは選択されず、入力欄は全て空（気づかないまま検索に送られないように）。`search_sort`・`search_songrange`・`search_jokerange`のcookieは保存されない |

| 初心者向け案内のデフォルト（#1236） | `is_shown_guide`クッキーなし | context["is_shown_guide"] = True、`#guide`が本文（`<article id="mainarticle">`）より前（`base.html`の`first_view`ブロック）に置かれ、「このサイトについて」「界隈曲とは」「すべあな界隈曲とは」の見出し（`<h2 class="guide-line">`）がある |
| 初心者向け案内の「表示しない」ボタン（#1236） | `is_shown_guide`クッキーなし | `<button type="button" id="guide-close" class="action-button black-action-button">`（`fa-times`のアイコンと「表示しない」）が1つあり、背景の画像（`#guide-image`）の中ではなく、`#guide-image`の後ろの兄弟要素の中にある |
| 初心者向け案内のcookieの保存期間（#1236） | `is_shown_guide`クッキーなし | `#guide`の`data-cookie-age`が`LONG_TERM_COOKIE_AGE`（`top.js`が閉じたときのcookieの保存期間に使う）。読み込み順に依存しないよう、インラインのスクリプトのグローバル変数（`guideCookieAge`）では渡さない |
| 初心者向け案内を閉じた後（#1236） | `is_shown_guide=off` | context["is_shown_guide"] = False、`#guide`と`data-cookie-age`が無い |
| 初心者向け案内のcookieの不正な値（#1236） | `is_shown_guide`が`on`・`OFF`・`<script>` | `off`以外は表示する。context["is_shown_guide"] = Trueで、`#guide`がある |
| 初心者向け案内の背景の画像（#1236） | — | `top.css`で背景にする画像は`url("../image/guide.webp")`の1つで、`finders.find`で見つかる（6周年記念グラフィックアートの`lyrics_default_hd.jpeg`をWebP（品質80）に変換したもの） |

初心者向け案内（#1236）の「表示しない」ボタン（背景の画像の下に置く）は、`top.js`で`is_shown_guide=off`のcookie（`path=/`・`max-age`は`#guide`の`data-cookie-age`・`samesite=lax`。設定画面で保存するcookieと同じ属性）を保存し、案内を消す。設定画面の「初心者向け案内の表示」で再び表示できる。案内を表示している間は、PCでキーワードの入力欄（「全て表示」の場合は`search_form.js`の`initSearchForm`で選択する入力欄）を選択しても、案内が画面の上から外れないようにスクロールしない（`focus({ preventScroll: true })`）。入力するとブラウザが入力欄までスクロールする。案内は本文の幅（800px）に収めず、背景の画像（`#guide-image`）を画面の幅いっぱい・ヘッダーの下から画面の下端（スマホのレイアウトでは下のメニューの上）までのファーストビュー全体に表示し、縦横比を変えずに上下か左右を切り取る（`background-size: cover`）。高さはヘッダー・下のメニューの高さ（`--guide-offset`）を引いて求める。`--guide-offset`は直値で持たず、ヘッダー・下のメニュー（`common.css`）と共有する`:root`の変数（`--header-top-height`・`--pc-header-menu-height`・`--pc-global-header-height`・`--header-border-width`・`--tab-bar-height`）から、ヘッダーと同じ条件（PCの上メニューは`data-pc-menu="header"`、それ以外はグローバルヘッダーを含む、スマホはグローバルヘッダーを含まず下のメニューを含む）で求める（PCの上メニュー112px・サイドメニュー94px・スマホ114px）。説明文が入りきらない低い画面では、説明文に合わせて縦に伸びる。画像の上に重ねる黒の不透明度は、説明文の範囲が90%（`--guide-opacity-center`・`--guide-opacity-text`）で、説明文の外側は画像の端まで30%（`--guide-opacity-edge`）にする。説明文は「。」の後で改行し、「界隈曲とは」「すべあな界隈曲とは」は見出しの後で改行する。説明文は`top.js`でフォントの読み込み後（約3MBのため、待つのは最大1sまで）に`.guide-line`を表示された1行ごと（スマホで折り返した行も1行とする。要素を書き換えずに`Range`で1文字ずつの位置を調べ、全ての行を調べてから書き換える）の`.guide-row`に分け、上の行から0.1sずつ遅らせて、0.5sかけて`ease-out`で下からフェードインする。表示し終えたら分ける前の文字に戻す（画面の幅を変えたときに折り返し直せるように）。JSが動かない場合は3s後にまとめて表示し、`prefers-reduced-motion: reduce`では動かさずに表示する。`top.js`の読み込みが遅く、3s後のまとめての表示が先に動いた場合は、行に分けて表示し直さない（文字が一度消えないように）。JSの動作と見た目はDjangoテストでは確認できないため、Playwrightで確認する（幅1920〜320px・横向きのスマホ、PCの上メニュー・サイドメニュー・`pc_menu_position`が不正な値のそれぞれで、`#guide-image`の上端がヘッダーの下端、下端が画面か下のメニューの上端と一致し、幅が画面の幅と一致すること）。

トップ画面の「全て表示」の検索フォームは、`top.js`で送信時に検索画面（`/songs/`）のURLクエリに変換して遷移する。テキスト等の入力欄・メディアは値がある場合のみ、ラジオボタン（並び替え・界隈曲・ネタ曲・真偽値のフィルタ）は表示時から選択を変更した場合のみURLクエリに含める。並び替え・界隈曲・ネタ曲は表示時に検索画面と同じcookieの値が選択されており、含めなくても検索画面で同じ値が選択されるため。song guesser・原曲ボタンのクリックでは模倣の曲IDを入力するのみで、遷移しない。JSの動作はDjangoテストでは確認できないため、Playwrightで確認する。

スマホメニューのフッターは、幅が狭い画面（幅320〜390px）では「プライバシーポリシー」のリンクが2行目に回る（#1170）。リンクの途中で改行せず、フッターの高さが広がってリンクがはみ出さないことはDjangoテストでは確認できないため、Playwrightで確認する。

#### 7-2. `SongsView` (`/songs/`)

検索フォームは`components/search_form.html`・`search_form.js`・`css/components/search_form.css`に切り出し、トップ画面の「全て表示」の検索と共通で使う。contextは`get_search_form_context`で作る。`search_form.css`は全ページでは読み込まず、使うページだけが`base.html`の`component_css`ブロックで読み込む。

カテゴリのフォーム（#423）は、カテゴリごとに「すべあな界隈曲」と同じ指定なし・のみ・以外のラジオボタン（`components/bool_filter.html`、`name="category_<カテゴリ>"`）を並べる。選択はまとめて`categorys`のクエリ（カンマ区切りで、「以外」のカテゴリは先頭に~を付ける。例：`arrange,~meme`）にし、`search_categorys` cookieにも同じ形式で保存する。Djangoはカンマを含むcookieの値を`"arrange\054~meme"`のように8進数でエスケープするため、`base.js`の`getCookie()`で元の文字に戻す。選択の変更時の保存（`songs.js`）・ブラウザバック時の復元（`search_form.js`の`restoreFormValuesFromCookies()`）はDjangoテストでは確認できないため、Playwrightで確認する。

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
| 模倣元のフォーム（#1241） | GETリクエスト | フォームを選ぶラジオボタンと`#imitate`のラベルが「模倣元」・模倣元のアイコン（`fas fa-sitemap imitate`）で表示される（入力した曲を模倣元に持つ曲で絞り込むため） |
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
| save_select=offのURLクエリは保存設定cookieを上書きしない（#376） | `is_saved_select=on`, `search_sort=-view`・`search_songrange=subeana` (cookie), `?sort=upload_time&songrange=xx&save_select=off`（トップ画面の投稿予定の「もっと見る」等のリンク） | context["sort"] = "upload_time"・context["songrange"] = "xx"（表示には反映）、`search_sort`・`search_songrange` cookieは保存されない |
| save_select=offでもURLクエリに無いフォームは保存した選択を使う（#376） | `is_saved_select=on`, `search_songrange=subeana`・`search_jokerange=off` (cookie), `?sort=upload_time&save_select=off` | context["songrange"] = "subeana"・context["jokerange"] = "off" |
| 検索フォームの初期表示（デフォルト） | URLクエリなし | context["search_form"] = "keyword"、キーワードのラジオボタンが選択され、他のフォームは `hidden` |
| 検索フォームのラジオボタンは必ず1つ選択される | URLクエリなし・各フォームのURLクエリ | `name="search-form"` のラジオボタンが常に1つだけ選択される（JSはこれを前提にしている） |
| 全てのフォームにURLクエリが対応づけられている | GETリクエスト | 20個のラジオボタンの並びが `SEARCH_FORM_QUERIES` のキーの並びと一致する |
| 真偽値のフィルタの不正な値 | `?is_lack=foo` | 「未完成」のフォームが表示され、「指定なし」のラジオボタンが選択される |
| mediatypesのURLクエリ | `?mediatypes=youtube,nicovideo,unknown` | URLのフォームが表示され、YouTube・ニコニコ動画のチェックボックスのみ選択される（存在しないメディアは無視） |
| mediatypes未指定 | URLクエリなし | メディアのチェックボックスは選択されない |
| カテゴリのフォーム（#423） | URLクエリなし | `Song.CHOICES` の順に全てのカテゴリの指定なし・のみ・以外のラジオボタンが表示され、全て指定なし（`data-default`）が選択される。チェックボックスは無い |
| カテゴリのラジオボタンのアイコン（#423） | GETリクエスト | 見出しに `SONG_CATEGORIES` のアイコンが付く（ネタ動画は `far fa-laugh-squint`） |
| categorysのURLクエリ（#423） | `?categorys=arrange,~meme,unknown,~unknown` | アレンジの「のみ」・ネタ動画の「以外」が選択され、`context["category_filters"]` の値と一致する（存在しないカテゴリは無視） |
| 保存したカテゴリの選択（#423） | `is_saved_select=on`, `search_categorys=arrange,~meme,unknown` (cookie) | アレンジの「のみ」・ネタ動画の「以外」が選択される。表示するフォームはキーワードのまま |
| 保存がoffのカテゴリの選択（#423） | `is_saved_select=off`, `search_categorys=arrange` (cookie) | 全て指定なし |
| categorysのURLクエリはcookieを上書きしない（#423） | `is_saved_select=on`, `search_categorys=meme` (cookie), `?categorys=~arrange` | アレンジの「以外」のみ選択され、`search_categorys` cookieは保存されない（曲ページのタグのリンク等の一時的な絞り込みのため） |
| カテゴリの選択の変更を保存（#423） | `is_saved_select=on`, `POST {categorys="~meme,unknown,arrange"}`（songs.jsのPOST） | `search_categorys` cookieに、選択肢にあるカテゴリのみを `SONG_CATEGORIES` の順にした `"arrange,~meme"` が `LONG_TERM_COOKIE_AGE` で保存される |
| 全て指定なしにした選択を保存（#423） | `is_saved_select=on`, `search_categorys=arrange` (cookie), `POST {categorys=""}` | `search_categorys` cookieに `""` が保存され、全て指定なし |
| 保存がoffのカテゴリの選択の変更（#423） | `is_saved_select=off`, `POST {categorys="arrange"}` | `search_categorys` cookieは保存されない |
| 並び替え等の変更（#423） | `is_saved_select=on`, `search_categorys=~arrange` (cookie), `POST {sort="-view"}` | `search_categorys` cookieは保存されず、アレンジの「以外」が選択される |
| 検索フォームの初期表示（URLクエリ指定） | `?title=テスト` `?mediatypes=youtube` `?categorys=arrange` `?view_gte=100` `?is_subeana=xx` `?jokerange=off` `?is_original=True` `?is_inst=True` `?is_questionable=True` `?is_special=True` `?is_collab=True` `?is_lack=True` `?sort=-view` など | URLクエリを含むフォーム（title/url/category/youtube/subeana/joke/original/inst/questionable/special/collab/lack/sortなど）が表示される |
| 検索フォームの初期表示（複数指定） | `?is_lack=True&keyword=テスト` / `?title=テスト&sort=-view` / `?title=テスト&view_gte=100` / `?view_gte=100&lyrics=テスト` | ラジオボタンの並び順で先の "keyword" / "sort" / "youtube" / "lyrics" が表示される |
| ラジオボタンの並び順 | GETリクエスト | よく利用するため、先頭からキーワード・並び替え・歌詞・YouTubeの順に並ぶ（全20個。プレラは#1064で追加） |
| プレラのフォーム（#1064） | 2021年・2024年（2件）・2025年の日付のプレラと、日付が無いプレラが登録されている | プレラのラジオボタン（`fas fa-angle-double-right` のアイコン）と、`<select id="prush" name="prush">` の選択肢が表示される。選択肢は「指定なし」（値は空）と、プレラの日付（`Prush.date`）の新しい順に並べ、年ごとの `<optgroup>`（「2025年」「2024年」「2021年」、日付が無いものは最後の「年が不明」）に分けたプレラの名前。`select` の値も `search_form.js` の `FORM_QUERIES` でクエリに入る。年のグループのラベルは太字にせず灰色（`search_form.css`）にする（ブラウザでの確認はPlaywright） |
| `prush` のURLクエリ（#1064） | `?prush=年末プレラ５`（曲ページのタグのリンク） | プレラのフォームを表示し、「年末プレラ５」の選択肢を選択した状態にする（`selected_prush`。テキストの入力欄ではないため `TEXT_FORMS` には含めない） |
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
| 検索フォームのCSSの読み込み（#585） | GETリクエスト | `css/components/search_form.css`が`songs.css`より先に読み込まれる |
| 検索フォームが無いページ（#585） | 設定画面・曲の新規作成画面にGETリクエスト | `css/components/search_form.css`が読み込まれない |
| 入力欄の一覧（#585） | GETリクエスト | フォームの文字・数値・日付の入力欄（`input type="text"`・`number`・`date`）の`name`が`TEXT_FORMS`と一致する（入力欄の初期値は`request.GET`ではなく`get_search_form_context`の`form_values`から入れるため） |
| 入力欄のURLクエリ（#585） | `TEXT_FORMS`の全ての入力欄に`<name>"<b>` | context["form_values"]にURLクエリの値が入り、各入力欄の`value`にエスケープされて（`&quot;&lt;b&gt;`）入る |
| 検索フォームのJSの読み込み順（#585） | GETリクエスト | トップ画面と共通の`search_form.js`が`songs.js`より先に読み込まれる |

#### 7-3. `SongView` (`/songs/<id>/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲ID | 有効なsong_id | HTTP 200 |
| 存在しない曲ID | 無効なsong_id | HTTP 404 |
| ユーザーが削除した曲（#1239） | `is_removed=True` の曲 | HTTP 410で、曲の情報（歌詞等）を表示せず、`<h1><曲名>のページは削除されました</h1>`と「削除を取り消す」ボタンのあるページ（`song_removed.html`、7-7-2）を表示する（#1264）。noindex |
| 削除を取り消した後のトースト（#1264） | `?toast=restore` | `showToast("ok", "削除を取り消しました。");`が含まれる |
| 通知に失敗した取り消しの後のトースト（#1264） | `?toast=restore_notify_error` | `showToast("warning", "削除を取り消しましたが、管理者への通知に失敗しました。");`が含まれる |
| 模倣元・模倣曲に削除した曲がある（#1239） | `is_removed=True` の曲と模倣関係がある | 模倣元・模倣曲の一覧（`imitate_list`・`imitated_list`）に含まれず、タイトルも表示されない |
| 「編集/削除」のボタン（#1239） | 有効なsong_id | ボタンの文言が「編集/削除」で、「削除申請」は含まれない |
| is_questionable=True の曲 | `is_questionable=True` の曲 | レスポンスに「界隈曲?」タグが含まれる |
| is_questionable=False の曲 | デフォルトの曲 | レスポンスに「界隈曲?」タグが含まれない |
| デフォルトの曲 | `is_questionable=False`, `is_limited=False` | レスポンスに `<meta name="robots">` が含まれない |
| is_questionable=True の曲 | `is_questionable=True` の曲 | レスポンスに `<meta name="robots" content="noindex, nofollow">` が含まれる |
| is_limited=True の曲 | `is_limited=True` の曲 | レスポンスに `<meta name="robots" content="noindex, nofollow">` が含まれる |
| フラグがない曲のタグ欄（#1228） | 未完成でなく、フラグがすべて既定値 | タグ欄（`<tr id="tags">`）が表示されない |
| スペシャルデザインだけの曲のタグ欄（#1228） | 未完成でなく、`is_special=True` だけ | タグ欄が表示され、スペシャルデザインのタグ（リンクなし）が出る |
| 未完成のタグ（#1228） | URL未登録の曲 | `?is_lack=True` の検索へのリンクのタグが出る |
| フィールドのフラグのタグ（#1228） | `is_draft=True`・`is_subeana=False` | `?is_draft=True`・`?is_subeana=xx` の検索へのリンクのタグが出る |
| 説明付きのタグ（#1228） | `is_questionable=True`・`is_limited=True` | リンクではなく、`data-tutorial` の説明のアイコン付きのタグが出る |
| 界隈曲?の非すべあな曲のタグ（#1228） | `is_questionable=True`・`is_subeana=False` | 界隈曲?のタグは出て、非すべあな模倣曲のタグは出ない |
| タグの順番（#1228） | `is_questionable=True`・`is_draft=True`・`is_limited=True`・URL未登録 | 界隈曲?・未完成・下書き・限定公開の順に並ぶ |
| カテゴリのタグ（#423） | `category="arrange"`・`is_questionable=True` | `?categorys=arrange` の検索へのリンクのタグ（カテゴリのアイコン `fas fa-sliders-h`、「アレンジ」）が、界隈曲?のタグより前に出る |
| プレラのタグ（#1064） | プレラ「端午プレラ6 / 端午クソ動画投稿祭6」の曲 | `?prush=<URLエンコードした名前>` の検索へのリンク（「＞＞」のような `fas fa-angle-double-right` のアイコンと名前）をタグに表示する |
| カテゴリだけの曲のタグ欄（#423） | 未完成でなく、`category="meme"` だけ | タグ欄が表示され、`?categorys=meme` のリンクのタグ（`far fa-laugh-squint`、「ネタ動画」）が出る |
| カテゴリが曲の曲（#423） | `category="song"`（既定値）・URL未登録 | カテゴリのタグは出ない（未完成のタグは出る） |
| 模倣元のdetails（#423） | 模倣元にカテゴリが曲の曲・ネタ曲・カバー・ネタ曲のアレンジ | 模倣元のdetailsの直下にカテゴリが曲の曲を並べ、ネタ曲（`far fa-meh-rolling-eyes`）・アレンジ（`fas fa-sliders-h`）・カバー（`fas fa-microphone`）の順に、それぞれのdetailsにまとめる。ネタ曲のアレンジはアレンジの方に入る |
| 模倣曲のdetails（#423） | 模倣曲にメドレーの曲 | 模倣曲のdetailsの中に、メドレー（`fas fa-stream`）のdetailsが出る |
| full 版の曲（#667） | 同じ名義の short 版が2曲ある | song-info に「short版」の行が2つあり、それぞれの曲へのリンクが表示される。「full版」の行は表示されない |
| short 版の曲（#667） | 同じ名義の full 版がある | song-info に「full版」の行があり、full 版の曲へのリンクが表示される |
| short 版・full 版がない曲（#667） | 関係する曲がない | 「full版」「short版」の行が表示されない |
| タイトルのエスケープ（#667） | full 版のタイトルが `<b>曲</b>` | リンクのタイトルがエスケープされて表示される |
| 年表で見るボタン（#1269） | `SongTimeline`（`sheet_id=123`・`row=45`・`is_lyrics_blank=False`）がある曲、`GOOGLE_SHEETS_SPREADSHEET_ID`を設定 | 「編集履歴」の右隣に、`https://docs.google.com/spreadsheets/d/<スプレッドシートのID>/edit#gid=123&range=45:45`（シートの45行目を選択した状態）を新しいタブで開く「年表で見る」ボタン（`fas fa-table`）を表示する。「年表に登録する」は表示しない |
| 年表に登録するボタン（#1269） | `is_lyrics_blank=True`（URL列で一致した行の歌詞列が空） | 「編集履歴」の右隣に、`#gid=123&range=O45`（歌詞列のセル。行を選択したまま貼り付けると行の全てのセルに入るため）を開く「年表に登録する」ボタン（`fas fa-table`と、検索フォームの`small-icon`と同じく小さくして5px空けた`fas fa-exclamation`、`id="timeline-register"`、`data-song-url="<ROOT_URL>/songs/<id>/"`）を表示し、「年表で見る」は表示しない。クリックすると曲のページのURLをコピーしてから年表を新しいタブで開き、開いたタブの`opener`を外す。コピーを待った後の`window.open`はSafari（特にiOS）でポップアップとしてブロックされることがあるため、`null`が返ればこのタブで年表を開く（nonce付きのscriptの`addEventListener`。`window.open`が`null`を返す場合も含めて動作はPlaywrightで確認） |
| 年表に載っていない曲（#1269） | `SongTimeline`が無い曲 | 「年表で見る」「年表に登録する」のボタンを表示しない |
| スプレッドシートのIDが無い（#1269） | `GOOGLE_SHEETS_SPREADSHEET_ID=""`・`is_lyrics_blank=True` | 「年表で見る」「年表に登録する」のボタンを表示しない |
| 埋め込みプレイヤー（#1254） | YouTubeのURLと歌詞がある曲 | `<details id="embed" data-cookie-age="<LONG_TERM_COOKIE_AGE>" open>`の中に、`<summary>`（`fas fa-play-circle`・「埋め込み」・サービス名「YouTube」）と、`youtube-nocookie.com/embed/<動画ID>`の`<iframe class="embed-frame embed-video" title="YouTubeの埋め込み" loading="lazy">`が出る。`#lyrics-wrapper`より前に置く |
| 埋め込みプレイヤーの位置（#1254） | 模倣元がある曲 | 模倣元のdetailsより後ろ、歌詞（`#lyrics-wrapper`）より前に表示する |
| 歌詞がない曲の埋め込みプレイヤー（#1254） | 歌詞が空で、YouTubeのURLがある曲 | 歌詞の欄（`#lyrics-wrapper`）はなく、埋め込みプレイヤーは表示する |
| 複数の埋め込み（#1254） | YouTube・ニコニコ動画・SoundCloudの曲のURL | `<iframe class="embed-frame`が3つ。SoundCloudは`embed-audio`で、`src`の`&`は`&amp;`にエスケープされる。`<summary>`に3つのサービス名が出る |
| 埋め込めるURLがない曲（#1254） | URLなし・Xのポストだけ | `id="embed"`の欄と`<iframe`を表示しない |
| 埋め込みプレイヤーの既定は開く（#1254） | `is_shown_embed`のcookieなし | `context["is_shown_embed"] = True`で、`<details id="embed" ... open>`になる |
| 閉じた埋め込みプレイヤー（#1254） | `is_shown_embed=off` | `context["is_shown_embed"] = False`で、`open`が付かない（`<iframe>`は出力し、`loading="lazy"`により閉じている間は読み込まれない） |
| `is_shown_embed`の不正な値（#1254） | `on`・`OFF`・`<script>` | `off`以外は開く。`is_shown_embed = True`で`open`が付く |
| 埋め込みプレイヤーの開閉の保存（#1254） | YouTubeのURLがある曲 | nonce付きのscriptの`embedEle.addEventListener('toggle'`で、開閉時に`is_shown_embed=on`・`off`を`path=/`・`max-age`（`data-cookie-age`）・`samesite=lax`のcookieに保存する。`onclick`は使わない。ブラウザの動作はPlaywrightで確認（結合テスト26章） |

#### 7-4. `SongNewView` (`/songs/new/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| GETアクセス | GETリクエスト | HTTP 200、フォームが表示される |
| POST: YouTube以外のURL | `url="https://example.com/..."` | HTTP 200、"YouTube" を含むエラー |
| POST: YouTube APIの呼び出しに失敗（#1146、#886） | YouTubeのURL・`get_youtube_api` が `YoutubeApiError` を送出 | 500エラーにならずHTTP 200で、「インターネットに接続できなかった」「YouTubeから動画の情報を取得できませんでした」を含むエラーをトーストで表示し、Songは作成されない（動画が削除・非公開とは限らないため、「削除」は含まない） |
| POST: インターネットに接続できない（#886） | YouTubeのURL・`get_youtube_api`内のAPIの呼び出し（`build`をモック）が`socket.timeout`を送出 | HTTP 200、「インターネットに接続できなかった」を含み「削除」を含まないエラー。Songは作成されない |
| POST: 動画が削除・非公開（#886） | YouTubeのURL・`get_youtube_api` が `{}` を返す | HTTP 200、「作者は空白にできません」ではなく、「YouTube上で削除されたか非公開になっている」「「タイトルと作者から登録」で「非公開/削除済み」にチェックを入れて」を含むエラーをトーストで表示し、Songは作成されない |
| POST: 既に登録されているYouTubeのURL | 曲に紐づく`SongLink`と同じURL | HTTP 200、"既に登録されています" を含むエラー。`get_youtube_api`は呼び出されない（クォータを消費しない） |
| POST: YouTubeのURLから登録 | `get_youtube_api` がタイトル・チャンネル名を返す | `/songs/<id>/edit`へリダイレクト（302）。Songのタイトル・作者・URLがAPIの結果・入力したURLで保存される |
| POST: プレラは登録できない（#1064） | `prush=年末プレラ５` を付けて送信 | 302、曲の `prush` は `None`（プレラは年表の取り込みでのみ登録する） |
| POST: YouTubeのライブのURLから登録（#52） | `url="https://www.youtube.com/live/<id>?si=xxxx"`・`get_youtube_api` がタイトル・チャンネル名を返す | 302。`get_youtube_api`は動画IDで呼ばれ、URLは`https://youtu.be/<id>`で保存される。画面のJS（`base.js`の`getYouTubeId`）もライブのURLを動画のURLとして扱う（Playwrightで確認） |
| POST: 作者が空白 | `url=""`, `authors="  "` | HTTP 200、"作者" を含むエラー |
| POST: タイトルが空 | `url=""`, `authors="テスト作者"`, `title=""` | HTTP 200、"タイトル" を含むエラー |
| POST: タイトルが`Song.title`のmax_length超（#1085） | `title`がmax_length+1文字 | HTTP 200、"タイトル" を含むエラー、Songは作成されない（フォームを経由せず保存するため直接バリデーションが必要） |
| POST: 作者名が`Author.name`のmax_length超（#1085） | `authors`がmax_length+1文字 | HTTP 200、"作者名" を含むエラー、Songは作成されない |
| POST: is-questionable時、オリジナル模倣は強制OFF・その他フラグの入力値はそのまま保存される | `is-questionable-manual=on`, `is-original-manual=on`, `is-subeana-manual=on` | 保存されたSongの `is_questionable=True`、`is_original=False`、`is_subeana=True` |
| POST: 作者名がpast別名と一致し統一した名義へ正規化される（#1029、#1137） | `authors=`past別名のname | 保存後、redirect先URLに`name_unified=1`が付与される |
| POST: 正規化が発生しない | `authors=`通常の作者名 | redirect先URLに`name_unified`は付与されない |
| GET: カテゴリの選択欄（#423） | GETリクエスト | 2つのフォームそれぞれに `<select id="category-auto/manual" name="category" data-sync="category">` が表示され、`Song.CHOICES` の全ての選択肢が2つずつある |
| POST: カテゴリを指定（#423） | `category="otomad"` | 302、保存されたSongの `category == "otomad"` |
| POST: カテゴリを指定しない（#423） | `category` なし | 302、保存されたSongの `category == "song"` |
| GET: 重複を許可するURLの入力欄（#1285） | GETリクエスト | URLで登録するフォームに `<input type="hidden" id="allow-dup-url" name="allow_dup_url">` が1つある |
| GET: `allow_dup_url`を付けて開いても重複を許可しない（#1285） | 曲に紐付くSongLinkのURLを`allow_dup_url`に付けてGET | HTTP 200、SongLinkは`allow_dup=False`のまま、Historyは作らず、Discordに通知しない |
| POST: 重複を許可して登録（#1282、#1285） | 曲Aに紐付くSongLinkのURLを`url`と`allow_dup_url`の両方に付けてPOST（`get_youtube_api`はモック） | 302、SongLinkが`allow_dup=True`になり、曲Aと新しい曲の両方が紐付く。曲Aに`history_type="edit"`のHistory（タイトル「<曲Aのタイトル>のURLの重複を許可」、編集者はリクエストのIPのEditor）が1件残り、新しい曲のHistoryは`new`だけ。Discordに「重複許可したURL」と「新規作成されました」を1回ずつ送る |
| POST: 重複を許可するURLの表記が違う（#1285） | `url`は`https://www.youtube.com/watch?v=<ID>`、`allow_dup_url`は`https://youtu.be/<ID>` | 302、同じ動画のURLとして重複を許可する |
| POST: 既に重複を許可したURLを重複を許可して登録（#1285） | `allow_dup=True`のSongLinkのURLを`url`と`allow_dup_url`に付けてPOST | 302、元から持つ曲にHistoryは作らない |
| POST: 重複を許可すると送らない（#1285） | 曲に紐付くSongLinkのURLを`url`に付け、`allow_dup_url`なしでPOST | HTTP 200、"既に登録されています" を含むエラー、`get_youtube_api`は呼び出されない。SongLinkは`allow_dup=False`のまま、Historyは作らない |
| POST: 重複を許可するURLが`url`と違う（#1285） | `url`は曲に紐付くSongLinkのURL、`allow_dup_url`は別の曲に紐付くSongLinkのURL | HTTP 200、"既に登録されています" を含むエラー。どのSongLinkも`allow_dup=False`のまま、Historyは作らない |
| POST: URLなしで`allow_dup_url`を送る（#1285） | `url=""`（タイトルと作者から登録）で、曲に紐付くSongLinkのURLを`allow_dup_url`に付けてPOST | 302、SongLinkは`allow_dup=False`のまま、Historyは作らない |
| POST: 曲を保存できなかったとき重複を許可しない（#1285） | 重複するURLを`url`と`allow_dup_url`に付け、`get_youtube_api`が`{}`を返す（動画が削除・非公開） | HTTP 200、"YouTube上で削除されたか非公開になっている" を含むエラー。SongLinkは`allow_dup=False`のまま、Historyは作らず、Discordに通知しない |
| POST: 不正なカテゴリ（#423） | YouTubeのURL・`category="joke"` | HTTP 200、`"カテゴリが不正です。"` のエラー。`get_youtube_api` は呼び出されず、Songは作成されない |

#### 7-5. `SongEditView` (`/songs/<id>/edit/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲のGET | 有効なsong_id | HTTP 200 |
| 存在しない曲のGET | 無効なsong_id | HTTP 404 |
| ユーザーが削除した曲のGET（#1239） | `is_removed=True` の曲 | HTTP 410で、曲の情報を表示せず、削除を取り消すボタンのあるページ（`song_removed.html`、7-7-2）を表示する |
| GET: ブラウザにキャッシュさせない（#1135） | 有効なsong_id | `Cache-Control`に`no-store`が含まれ、`public`は含まれない（キャッシュされた古いフォームの送信で、その間の編集が巻き戻るのを防ぐ） |
| POST: is_questionable時に歌詞・模倣・下書き・オリジナル模倣が強制的に空/OFF | `is_questionable=True`, `lyrics="..."`, `imitate="<id>"`, `is_draft=True`, `is_original=True` | 保存されたSongの `lyrics=""`、`imitates`が空、`is_draft=False`、`is_original=False`、`is_questionable=True` |
| POST: is_questionable時も非公開/削除済み・ネタ曲・インスト・すべあな界隈曲は保存される | `is_questionable=True`, `is_deleted=True`, `is_joke=True`, `is_inst=True`, `is_subeana=True` | 各フラグがそれぞれ `True` のまま保存される |
| GET: カテゴリの選択欄（#423） | `category="medley"` の曲 | `<select id="category" name="category">` が表示され、メドレーの選択肢のみ `selected` |
| GET: 歌詞の入力欄（#423） | GETリクエスト | 歌詞の `.form-col` に `data-hide-if-not-song` が付く（カテゴリが曲以外のときに `song_edit.js` で非表示にする） |
| GET: 模倣元の入力欄（#1241） | GETリクエスト | `#imitate-label` が「模倣元」・模倣元のアイコン（`fas fa-sitemap imitate`）で表示され、原曲以外の曲を検索する欄の補足（`#imitate-sub`）が「もしくは原曲以外から選択」と表示される |
| GET: 重複を許可するURLの入力欄（#1285） | GETリクエスト | `<input type="hidden" id="allow-dup-url" name="allow_dup_url">` が1つある |
| GET: `allow_dup_url`を付けて開いても重複を許可しない（#1285） | 別の曲に紐付くSongLinkのURLを`allow_dup_url`に付けてGET | HTTP 200、SongLinkは`allow_dup=False`のまま、Historyは作らず、Discordに通知しない |
| POST: 重複を許可して登録（#1282、#1285） | 別の曲Aに紐付くSongLinkのURLを`url`と`allow_dup_url`の両方に付けてPOST | 302、SongLinkが`allow_dup=True`になり、曲Aと編集している曲の両方が紐付く。URLを元から持つ曲Aに`history_type="edit"`のHistory（タイトル「<曲Aのタイトル>のURLの重複を許可」）が1件残り、編集している曲には「重複を許可」のHistoryを作らない。Discordに「重複許可したURL」を1回送る |
| POST: 複数のURLのうち一部だけ重複を許可（#1285） | 別の曲に紐付く2つのURLを`url`にカンマ区切りで付け、`allow_dup_url`には一方だけ付けてPOST。続けて両方を`allow_dup_url`に付けてPOST | 1回目は HTTP 200、"既に登録されています" を含むエラーで、どちらのSongLinkも`allow_dup=False`のまま、URLは追加されない。2回目は 302、両方のSongLinkが`allow_dup=True`になり、2件のURLが紐付く |
| POST: 重複を許可すると送らない（#1285） | 別の曲に紐付くSongLinkのURLを`url`に付け、`allow_dup_url`なしでPOST | HTTP 200、"既に登録されています" を含むエラー。SongLinkは`allow_dup=False`のまま、Historyは作らない |
| POST: 重複を許可するURLが`url`と違う（#1285） | `url`は別の曲に紐付くSongLinkのURL、`allow_dup_url`は別のURL | HTTP 200、"既に登録されています" を含むエラー。SongLinkは`allow_dup=False`のまま |
| POST: 編集している曲にしか紐付いていないURLを`allow_dup_url`に付ける（#1285） | 編集している曲だけに紐付くSongLinkのURLを`url`と`allow_dup_url`に付けてPOST | 302、SongLinkは`allow_dup=False`のまま、「重複を許可」のHistoryは作らず、Discordに「重複許可したURL」を通知しない |
| POST: 編集している曲と別の曲に紐付くURLの重複を許可（#1285） | 編集している曲と別の曲Aの両方に紐付くSongLinkのURLを`url`と`allow_dup_url`に付けてPOST | 302、SongLinkが`allow_dup=True`になり、「重複を許可」のHistoryは曲Aにだけ1件でき、編集している曲にはできない |
| POST: 重複を許可するURLでもURLの長さを検証（#1285） | `url`と`allow_dup_url`にmax_length超のURL | HTTP 200、"文字以下である必要があります" を含むエラー、URLは追加されない |
| POST: 曲を保存できなかったとき重複を許可しない（#1285） | 重複するURLを`url`と`allow_dup_url`に付け、`authors`が`Author.name`のmax_length超 | HTTP 200、"作者名" を含むエラー。SongLinkは`allow_dup=False`のまま、Historyは作らず、Discordに通知しない |
| POST: カテゴリの変更（#423） | `category="omnibus"` | 302、`category == "omnibus"`、Historyの `changes` に `["カテゴリ", "曲", "総集編"]` |
| POST: カテゴリを送らない（#423） | `category="offv"` の曲に `category` なしで送信 | 302、`category == "offv"` のまま（カテゴリの選択欄がない古いページから送信された場合に変えない） |
| POST: プレラは変えられない（#1064） | プレラ「年末プレラ５」の曲に `prush=晩夏プレラ6` を付けて送信 | 302、タイトルは変わり、`prush` は「年末プレラ５」のまま（編集してもプレラは消えない） |
| POST: 不正なカテゴリ（#423） | `category="joke"` | HTTP 200、`"カテゴリが不正です。"` のエラー、カテゴリは変わらない |
| POST: カテゴリが曲以外でも歌詞は保存（#423） | `category="medley"`, `lyrics="歌詞"` | 302、`lyrics == "歌詞"`（歌詞の入力欄は非表示にするだけで消さない） |
| POST: 作者名が`Author.name`のmax_length超（#1085） | `authors`がmax_length+1文字 | HTTP 200、"作者名" を含むエラー |
| POST: 作者名がpast別名と一致し統一した名義へ正規化される（#1029、#1137） | `authors=`past別名のname | 保存後、redirect先URLに`name_unified=1`が付与される |
| POST: 正規化が発生しない | `authors=`通常の作者名 | redirect先URLに`name_unified`は付与されない |
| POST: ビリビリ動画のURL（#1246） | `url="https://www.bilibili.com/video/av417727107/?spm_id_from=...,https://www.bilibili.com/video/BV1in4y1Q7qw?p=2&vd_source=..."` | 302、`https://bilibili.com/video/BV1qV411J7Kq`・`https://bilibili.com/video/BV1in4y1Q7qw?p=2` で保存される |
| POST: 登録済みのBV番号のURLと同じ動画のav番号のURL（#1246） | 別の曲に `https://bilibili.com/video/BV1qV411J7Kq` が紐付いている状態で `url="https://www.bilibili.com/video/av417727107/"` | HTTP 200、"既に登録されています" を含むエラー、URLは追加されない |

#### 7-6. `ContactView` (`/contact/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| GETアクセス | GETリクエスト | HTTP 200 |
| POST: 正常な入力 | `category="不具合の報告"`, `detail="..."` | HTTP 200、`context["result"] == "ok"` |
| POST: 不正な入力 | `detail` 未入力 | HTTP 200、`context["result"]` にエラーメッセージ |
| クエリで入力した状態で開く | `?category=提案&detail=...`（曲の編集画面のリンク等） | 種類の「提案」が選択され、詳細に`detail`の値が入る |
| 種類に「削除の取り消し」が無い（#1264） | GETリクエスト | 「削除の取り消し」が含まれない（削除の取り消しは曲のページのボタンで行う） |

#### 7-7. `SongDeleteView` (`/songs/<id>/delete/`)

削除申請ではなく、送信するとすぐに曲を論理削除する（#1239）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲のGET | 有効なsong_id | HTTP 200 |
| 存在しない曲のGET | 無効なsong_id | HTTP 404 |
| GET: 削除のフォーム | 有効なsong_id | 削除した曲が表示されなくなる旨と、誤って削除した場合は曲のページの「削除を取り消す」から元に戻せる旨（#1264）の説明と「削除」の送信ボタンがあり、「削除申請」は含まれない |
| POST: 正常な削除理由 | `reason="..."` | 削除した曲のページは表示できないため、`/?toast=delete`（トップ）へリダイレクト |
| POST: 曲を論理削除する | `reason="..."` | `is_removed=True`になり、曲のページが削除した曲のページ（HTTP 410）になる |
| POST: 編集履歴を保存する | `reason="削除理由テスト"` | `history_type="delete"`・`title="<タイトル>を削除"`・`changes=["理由", "削除理由テスト"]`のHistoryが作成される |
| POST: Discordに通知する | `send_discord`をモック | 申請ではなく曲の変更になったため、新規登録・編集と同じNEW_DISCORD_URL宛に、`削除されました`・曲のページのURLで始まり、削除理由を含む文面を送る |
| POST: Discordに送信できない | `send_discord`が`False`を返す | 曲は削除されているため、500ページにはせず`/?toast=delete_notify_error`へリダイレクトする。曲は削除され、Historyも作成される |
| POST: 削除理由が空 | `reason=""` | HTTP 200、`context["error"]` にエラーメッセージ。曲は削除されない |
| 削除した曲（#1239） | `is_removed=True` の曲にGET・POST | どちらも削除した曲のページ（HTTP 410）。Historyは作成されない |
| 編集できない曲 | `is_lock=True` の曲にPOST | `/songs/<id>?toast=lock` へリダイレクトし、曲は削除されない |

#### 7-7-1. 管理サイトの曲（`SongAdmin`）（#1239）

ユーザーが削除した曲も表示し、`is_removed`のチェックを外して復元できるようにする

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 一覧に削除した曲を含める | `is_removed=True`の曲と通常の曲 | 一覧にどちらも表示される |
| 削除した曲で絞り込む | `?is_removed__exact=1` | 削除した曲だけが表示される |
| 削除した曲の変更画面 | `is_removed=True`の曲 | HTTP 200で、`is_removed`のチェックボックスがチェックされた状態で表示される |

#### 7-7-2. 削除した曲のページ（`song_removed.html`）（#1264）

曲のページ・編集・削除・編集履歴のページで、ユーザーが削除した曲（#1239）なら表示する（HTTP 410）。曲名・直近の削除理由と、削除を取り消す理由の入力欄（必須、#1275）・削除を取り消すボタンを表示する

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 曲名のエスケープ | タイトルが`<b>削除ページテスト曲</b>` | `<h1>&lt;b&gt;削除ページテスト曲&lt;/b&gt;のページは削除されました</h1>` |
| 直近の削除理由 | 削除（古い理由）→取り消し（取り消した理由）→削除（新しい理由）の履歴 | `<p id="song-removed-reason">削除理由：新しい削除理由</p>`が表示され、古い削除理由・取り消した理由は表示されない |
| 削除理由のエスケープと改行 | 理由が`<script>重複</script>`と改行・2行目 | エスケープされ、改行が`<br>`になる |
| 削除の履歴が無い | 管理サイトで削除した曲 | 「削除理由」は表示されない |
| 最新の履歴が削除ではない | 削除→取り消し（理由あり）の後に管理サイトで削除した曲 | 取り消す前の削除の理由・取り消した理由は表示されない |
| 削除の履歴のchangesが想定外の形 | `changes`が`None`・`[]`・`["理由"]`・`"理由"`の削除の履歴 | 500にならず、HTTP 410で「削除理由」は表示されない |
| 削除を取り消すボタン | 削除した曲 | `/songs/<id>/restore/`にPOSTするフォーム（`csrfmiddlewaretoken`付き）と、`<i class="fas fa-trash-restore-alt"></i>`・「削除を取り消す」のボタンがある |
| 取り消し理由の入力欄（#1275） | 削除した曲 | 上の削除理由と区別できるよう、フォームは区切り（`<div id="song-restore">`、`#song-restore`に区切り線）で分け、`<h1>削除を取り消す</h1>`と「この曲を元に戻す場合は、取り消す理由を入力してください。」の説明を付ける。その中に`<label for="restore-reason">取り消し理由</label>`と、`<textarea id="restore-reason" name="reason" required>`がある。削除を取り消すボタンは`disabled`で表示し、`song_removed.js`を読み込む（理由を入力すると押せるようになる。動作はPlaywrightで確認する）。エラーのトースト（`showToast(`）は出さない |
| お問い合わせでの申請を案内しない | 削除した曲 | 「削除の取り消し」「申請」が含まれない |
| ロックされた曲 | `is_lock=True` | 「この曲はロックされているため、削除を取り消せません。」と表示し、ボタン・理由の入力欄・フォームの区切り（`#song-restore`）は無い |
| URLが他の曲に登録されている | 削除した曲のURLが削除していない他の曲にも紐付く | 「この曲のURLが次の曲に登録されているため、削除を取り消せません。」と、その曲へのリンク（タイトルはエスケープ）を表示し、ボタンは無い |
| ブラウザにキャッシュさせない | 削除した曲 | `Cache-Control`が`no-cache`（削除を取り消した後に開き直したとき、キャッシュからこのページを表示しない） |

#### 7-7-3. `SongRestoreView` (`/songs/<id>/restore/`)（#1264）

削除した曲のページの「削除を取り消す」ボタンから、曲の削除を取り消す

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| POST: 削除を取り消す | 削除した曲 | `/songs/<id>?toast=restore`へリダイレクト（`X-Robots-Tag: noindex, nofollow`）。`is_removed=False`になり、曲のページがHTTP 200になる |
| POST: 編集履歴を保存する | 削除した曲、取り消しの理由 | `history_type="restore"`（表示名「削除の取り消し」）・`title="<タイトル>の削除を取り消し"`・`changes=["理由", <理由>]`（削除と同じ形）・送信した人の編集者のHistoryが作成される |
| POST: Discordに通知する | `send_discord`をモック | NEW_DISCORD_URL宛に、`削除が取り消されました`・曲のページのURLで始まり、`理由：<理由>`を含む文面を送る |
| POST: 取り消しの理由が無い（#1275） | `reason`を送らない・空・空白と改行だけ | 削除した曲のページ（HTTP 410）に`showToast("error", "取り消し理由を入力してください。");`を表示し、取り消さない。Historyの作成・Discordへの通知をしない |
| POST: Discordに送信できない | `send_discord`が`False`を返す | 500ページにはせず`/songs/<id>?toast=restore_notify_error`へリダイレクトする。削除は取り消され、Historyも作成される |
| GET | 削除した曲 | HTTP 405。削除は取り消されない |
| CSRFトークンが無い | `enforce_csrf_checks=True`でPOST | HTTP 403。削除は取り消されない |
| 存在しない曲 | 無効なsong_id | HTTP 404 |
| 削除していない曲 | 既に取り消した曲にPOST（理由あり・理由なし） | `/songs/<id>`へリダイレクトし、Historyの作成・Discordへの通知をしない。理由の確認より前に、削除しているかを確認する |
| ロックされた曲 | `is_lock=True`の削除した曲にPOST（理由あり・理由なし） | 削除した曲のページ（HTTP 410、ロックの説明）を返し、取り消さない。Historyの作成・Discordへの通知をしない。理由なしでも、理由のエラーではなくロックの説明を表示する |
| URLが他の曲に登録されている | 削除した曲のURLが他の曲にも紐付く状態でPOST | 削除した曲のページ（HTTP 410、登録している曲へのリンク）を返し、取り消さない。Historyの作成・Discordへの通知をしない |
| 削除と取り消し | 曲を削除した後に取り消す | 削除した曲のページに削除理由が表示され、取り消すと曲のページがHTTP 200になる。Historyは削除・取り消しの順に残り、どちらも`changes=["理由", <理由>]` |
| 曲の行のロック | `SELECT ... FOR UPDATE`に対応するDB（SQLiteでは実行しない） | 削除されているか・取り消せるかの確認より前に、曲の行を`SELECT ... FOR UPDATE`でロックし、その後に`UPDATE`する |
| 同時に押す（`TransactionTestCase`） | 1つ目の取り消しをコミット前に止め、その間に別の接続から2つ目をPOST（どちらも理由あり） | 2つ目は1つ目のコミットまでロックを待ち、削除していない曲として扱う。取り消し（`restore_song`）は1回だけ行われ、`history_type="restore"`のHistoryは1件 |

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
| 曲の検索ボタン (#954) | 正常アクセス | `.action-buttons`内に、`/songs/?author=<作者名をURLエンコードした値>` へのリンク（`fa-search`アイコン）が含まれる |
| 曲の検索ボタンのURLエンコード (#954) | 作者名に`&`・`=`・`+`・`#`・空白を含む | `author`クエリの値がURLエンコードされ、他のクエリや`#`以降として解釈されない |
| 統計ボタンのリンク (#334) | 正常アクセス | `/authors/<id>/stats/` へのリンクが含まれる |
| 統計ボタンのアイコン (#334) | 正常アクセス | `fa-chart-line`アイコンが含まれる |
| 統計ボタン下のメッセージ (#334、#968で鍵歴表示に変更。#1099でpt表示に変更) | 曲にview=1234を設定 | 鍵歴(`context["kenreki"]["points"]`、1234は7段階到達で7pt）がそのまま表示される（鍵盤数(7//2=3)には変換しない） |
| 統計ボタン下のメッセージの非表示 (#968) | authorに曲が1件も無い | `#author-stats-summary`自体が表示されない（`context["kenreki"]`が`None`） |
| 並び替えのデフォルト (#606) | URLクエリ・cookieなし | 従来通り登録日の遅い順（`-id`）で、`-id`の`<option>`が選択される |
| URLクエリの並び替え (#606) | `?sort=upload_time` | 投稿日の早い順で、投稿日の無い曲は末尾に表示される |
| 並び替えの選択肢 (#606) | 曲が2件以上 | `data-auto-submit`のGETフォームに、曲の検索画面と同じ`SORT_CHOICES`の`<option>`が同じ順で並ぶ |
| 並び替えの非表示 (#606) | 曲が1件 | 並び替えのフォーム（`#author-sort`）が表示されない |
| YouTubeの並び替えの案内 (#606) | `SORT_CHOICES`の各値で`?sort=` | `YOUTUBE_SORTS`の場合のみ`#author-sort-note`（YouTubeの情報が無い曲は最後に表示される旨）が表示される |
| 不正な並び替え (#606) | `?sort=invalid` | HTTP 200、デフォルト（`-id`）で表示し、cookieは保存しない |
| 並び替えのcookie保存 (#606) | `?sort=-view`（`is_saved_select`未設定） | `author_sort`に`-view`が`max-age=LONG_TERM_COOKIE_AGE`で保存される |
| 並び替えのcookieを保存しない (#606) | `is_saved_select=off`で`?sort=-view` | `-view`で表示するが、`author_sort`は保存しない |
| 保存された並び替え (#606) | `author_sort=-upload_time`のcookie、URLクエリなし | 投稿日の遅い順で表示される |
| 保存された並び替えを使わない (#606) | `is_saved_select=off`、`author_sort=-upload_time` | デフォルト（`-id`）で表示される |
| 不正なcookie (#606) | `author_sort=invalid` | デフォルト（`-id`）で表示される |
| ブラウザにキャッシュさせない (#606) | 正常アクセス | `Cache-Control`に`no-store`が含まれ、`public`は含まれない（cookieで並び順が変わるため、キャッシュされた古い並び順を表示しない） |
| 説明文は並び替えに依存しない (#606) | `?sort=-id`・`upload_time`・`random` | `context["description"]`が全て同じ（登録日の遅い順の曲名） |

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
| クエリ数の回帰防止 | Cの一覧を表示（A・Dはauthor_id解決済み、B・Eは未解決） | ビューの総クエリ数が想定通り（11件。10件目は#1008の名義の統一先の候補一覧の取得、11件目は#1230の、Cの名前を以前の名称として登録しているAへ名義が統一されているかどうかの判定用のCの曲数の取得）に収まる |
| 補完クエリの対象範囲 | 同上 | 補完クエリのIN句にB・Eの名前のみが含まれ、解決済みのA・Dの名前は含まれない |

##### 名義が統一されているかどうかの表示（#1230）

**テストクラス**: `AuthorAliasesUnifyNameStatusTest`

「名義を統一する」の見出しの下に、名義が統一されているかどうかを表示する。統一するボタンを押さなくても（押して「既に名義は統一されています。」のトーストが出るかどうかで確かめなくても）分かるようにするため。

- 統一先側（`#unify-name-status`）: authorがpast別名を持つ場合に、統一するフォームの上に表示する。判定は`get_ununified_source_authors()`（16-4-2）で、`AuthorUnifyNameSetView`で`unify_noop`になる条件と同じ
- 統一元側（`#unify-name-successor-status`）: 他のauthorがこのauthorの名前をpast別名として登録している（別名一覧に「その後の名称」として表示される）場合に表示する。このauthorに曲が残っていれば、まだその作者に統一されていない。統一はその作者の別名一覧で行うため、統一するフォームは表示しない。判定には`TransitiveAlias.is_direct_successor`（11-3-3）を使う。`group`以外の別名の名前はDB制約で全体でユニークなため、このauthorの名前をpast別名として登録できる作者は1人までで、表示も1件になる

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| past別名と同名のAuthorが無い | past別名のみ登録 | `#unify-name-status`が`.ok`で、`fa-check-circle`と「名義は統一されています」 |
| past別名と同名のAuthorが曲を持たない | 統一済みで曲数0のAuthorが残っている状態（#1137） | 「名義は統一されています」 |
| past別名と同名のAuthorが曲を持つ | そのAuthorが2曲を持つ | `.info`で`fa-info-circle`と「名義が統一されていません」、「2曲」、そのAuthorの作者ページへのリンク。統一されていないことは誤りではないため、`.warning`は使わない |
| 複数のAuthorが曲を持つ | 1曲が2つのpast別名のAuthorの共著、3つ目のpast別名のAuthorは曲を持たない | 「1曲」（共著は1曲として数える）。曲を持つ2つのAuthorへのリンクを含み、曲を持たないAuthorへのリンクは含まない |
| 統一するフォームと同じ順に並べる | 別名の登録順と、Authorのid順・名前順が逆になるようにする | 統一されていないAuthorが別名の登録順（統一するフォームの候補の順）に並ぶ |
| past以外の別名と同名のAuthorは対象外 | `another`別名と同名のAuthorがSongを持つ | 「名義は統一されています」 |
| 統一すると表示が変わる | 「統一されていません」の状態から、現在の名義のまま`AuthorUnifyNameSetView`へPOST | 「名義は統一されています」に変わる |
| 統一に関係しないauthor | past別名を持たず、他のauthorのpast別名にもなっていない | 状態の表示も「名義を統一する」の見出し（`data-tutorial="unify-name"`）も表示しない |
| 統一元側・曲が残っている | 他のauthorがこのauthorの名前をpast別名として登録し、このauthorが1曲を持つ | `#unify-name-successor-status`が`.info`で、`fa-info-circle`と「この作者の曲が1曲あり、名義が『<その作者>』に統一されていません」、その作者の別名一覧へのリンク。「名義を統一する」の見出しは表示するが、統一するフォームと`#unify-name-status`は表示しない |
| 統一元側・曲が無い | 同上で、このauthorが曲を持たない | `.ok`で、「名義は『<その作者>』に統一されています」と、その作者の作者ページへのリンク |
| 統一元側・past以外は対象外 | 他のauthorがこのauthorの名前を`another`別名として登録 | `#unify-name-successor-status`は表示しない |
| 統一元側・作者名のエスケープ | その作者の名前が`<b>その後の名義</b>` | エスケープされて表示される |

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
| `alias_type`がpast以外の別名を選択 | `name=`another等の別名のname | 変更されず、`?toast=unify_invalid`付きでリダイレクト（候補にない名義はページの再読み込みで直るため、「時間をおいて」の文言を使う`unify_error`ではない、#1290） |
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
| 旧名(old_name)が既存の別名と衝突 | old_nameと同名の`AuthorAlias`をauthor・統一先以外の別authorが既に保有（「逆方向」の関係として正常にありうる状態） | `AuthorAlias.name`のグローバルなunique制約により再登録が決定的に失敗するため、Discord通知を送る前に検知して`?toast=unify_conflict&conflict=<別authorのid>`へリダイレクトする（待っても直らないため、原因の作者を別名一覧画面で伝える、#1290）。`send_discord()`は呼ばれない。DB・Historyも変更されない |
| 旧名の衝突・統一先が既存の別Author（#1290） | 統一先が既存の別Authorで、old_nameと同名の別名を第三者のauthorが保有（本番で起きたケース） | 同じく`?toast=unify_conflict&conflict=<第三者のid>`へリダイレクトし、`send_discord()`は呼ばれず、Historyも作成されない |
| 旧名と同名の別名を統一先自身が保有（#1290） | 統一先のAuthorがold_nameと同名の`past`別名を持つ | 衝突ではなく、その別名を再利用して統一に成功する（`?toast=unify`） |
| 別名一覧画面の衝突理由の表示（#1290） | `?toast=unify_conflict&conflict=<id>`で、そのauthorがauthor名と同名の別名を持つ | `#unify-name-conflict`に「『現在の名義』は統一後の名前の以前の名称として登録されますが、」と、衝突している作者の別名一覧へのリンクが表示される |
| 衝突理由は実在する衝突のみ表示（#1290） | `conflict`に、author名と同名の別名を持たない作者のidを指定 | `#unify-name-conflict`も、その作者の名前も表示されない（クエリを書き換えた偽の理由を出さない） |
| 衝突理由の不正なクエリ（#1290） | `conflict`が`abc`・`-1`・`1.5`・SQLiteの整数の上限を超える値・5000桁の数字・全角数字・`²` | HTTP 200のまま`#unify-name-conflict`は表示されない（500にならない）。idの検証は`parse_sqlite_id()`（13-2） |
| 衝突する作者が表示件数の上限ちょうど（#1290） | `group`別名で旧名と同名を持つ作者が`UNIFY_CONFLICT_DISPLAY_LIMIT`（5）人 | `?toast=unify_conflict&conflict=<id>`を5件付けてリダイレクトし、`conflict_more`は付けない |
| 衝突する作者が表示件数の上限を超える（#1290） | 上と同じ作者が上限+2人（確認画面は上限+1人） | idは先頭の上限までの5件だけをクエリに載せ、超えた分は`conflict_more=<件数>`で渡す（受け取り側が切り捨てるidを渡さない）。確認画面でも同じ |
| 超過分を「ほかN件」で表示（#1290） | `conflict`に上限と同じ5人分のid、`conflict_more=3` | `#unify-name-conflict`に5人へのリンクが並び、「ほか3件の別名に同じ名前が登録されており、」と表示される |
| `conflict_more`なし（#1290） | `conflict`に5人分のidのみ | 「ほか」を表示しない |
| 上限まで表示していないときは`conflict_more`を使わない（#1290） | `conflict`に実在する4人分のid、`conflict_more=3` | 「ほか」を表示しない（クエリを書き換えて件数だけを出せないようにする） |
| `conflict_more`の不正な値（#1290） | `abc`・`-1`・`1.5`・SQLiteの整数の上限を超える値・全角数字・空文字 | HTTP 200のまま「ほか」を表示しない（500にならない） |
| クエリのidが上限を超えて並ぶ（#1290） | `conflict`に上限+1人分のid | リンクとして表示するのは先頭の上限（5人）まで。判定は、別名一覧の上部にも衝突する作者の行が表示されるため、`#unify-name-conflict`の中だけを見る |
| `toast`なしでは衝突理由を出さない（#1290） | `conflict`のみ指定し、`toast=unify_conflict`は無い | `#unify-name-conflict`は表示されない |
| 統一の失敗ごとのトースト文言（#1290） | `toast=unify_conflict`・`unify_invalid`・`unify_error` | それぞれ「別名の名前が重複しているため、名義を統一できませんでした。」「選択された名義は統一できません。ページを再読み込みして、もう一度お試しください。」「名義を統一できませんでした。時間をおいて再度お試しください。」が表示される。待っても直らない失敗には「時間をおいて」を使わない |
| 別名一覧画面のフォーム表示 | authorが`alias_type="past"`の別名を持つ | フォーム（`#unify-name-form`）と「名義を統一する」の見出し、チュートリアルアイコン（`data-tutorial="unify-name"`、#1126でインラインのonclickから変更）が表示される。フォームの送信先は確認画面（`AuthorUnifyNameConfirmView`） |
| 別名一覧画面のフォーム非表示 | authorが`alias_type="past"`の別名を持たない | フォームは表示されない（選択肢が現在の名前1件のみのため） |
| フォームの並び（#1137） | authorが`alias_type="past"`の別名を持つ | 「[ ] 以前の名称 ↓ [x] 現在の名義」の順に、past別名・矢印（`#unify-name-arrow`）・現在の名義が並び、初期状態では現在の名義のみが`checked`になる。選択を変えると、選択した名義が矢印の下へ移動する（JSによるDOM操作のため手動確認） |
| 統一するボタン（#1137） | authorが`alias_type="past"`の別名を持つ | `#unify-name-submit`ボタンは`disabled`ではなく（フォームを変更しなくても統一できる）、ラベルは「統一する」 |

#### 7-8-6. `AuthorUnifyNameConfirmView` (`/authors/<id>/aliases/unify/confirm`)（#1029, #1137）

名義の統一前に内容を確認させるための画面。統一により他のAuthorの曲が統一先へ移ることをIPベースの匿名編集者でも実行できてしまうため、実際の統一前にワンクッション挟む安全策。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在しないauthor_id | 無効なauthor_id | HTTP 404 |
| 無効な名義 | 候補にない`name` | 確認画面を表示せず`?toast=unify_invalid`付きで別名一覧へリダイレクト（#1290） |
| 現在の名前を選択し、移す曲もない | `name=author.name`、移す曲がない | 確認画面を表示せず`?toast=unify_noop`付きで別名一覧へリダイレクト |
| 旧名が別authorの別名と衝突（#1290） | old_nameと同名の`AuthorAlias`をauthor・統一先以外の別authorが保有し、past別名を選択 | 確認画面を表示せず`?toast=unify_conflict&conflict=<別authorのid>`付きで別名一覧へリダイレクト。確認して確定した後ではなく、確認画面に進む前に理由を伝えるため |
| 旧名の衝突・統一先が既存の別Author（#1290） | 上記で、選択したpast別名と同名の既存Authorが統一先になる | 同じく`?toast=unify_conflict&conflict=<別authorのid>`付きでリダイレクト |
| 衝突する作者が表示件数の上限を超える（#1290） | `group`別名で旧名と同名を持つ作者が上限+1人 | 先頭の上限（5人）までのidと`conflict_more=1`を付けて別名一覧へリダイレクト |
| 現在の名前を選択した場合は衝突しない（#1290） | 別authorがold_nameと同名の別名を持つが、`name=author.name`で移す曲がある | 旧名の再登録が起きないため、HTTP 200で確認画面が表示される |
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
| ユーザーが削除した曲のHistory（#1239） | 曲の削除のHistoryを作成した後に`is_removed=True` | 曲のページは404になるため、曲のページへのリンクは無く「この曲または作者は削除されました」が表示される。削除理由は表示される |
| 削除を取り消した曲のHistory（#1264） | 曲を削除してから取り消す | 「<タイトル>の削除を取り消し」が表示され、削除・取り消しの両方の履歴から曲のページへリンクする。「この曲または作者は削除されました」は表示されない |
| 検索欄のラベル（#954） | 正常アクセス | 検索欄（`input[name="q"]`）に`aria-label="編集履歴の概要で検索"`が付く（編集者のページと共通の`history_search_form.html`） |
| ページ送りで検索語を引き継ぐ（#954） | `?q=別名`で検索結果が`HISTORIES_PER_PAGE`件を超える | 「次へ」が`?page=2&q=<URLエンコードした検索語>`、2ページ目の「前へ」が`?page=1&q=<同>`へのリンクになる（共通の`pagination.html`） |
| 非公開の編集者の履歴に報告リンク（#1294） | `is_open=False`の編集者の履歴、`?q=報告&page=1` | 「編集者: 非公開」の横に`a#history-report-<履歴のid>`（`rel="nofollow"`）があり、`/histories/<履歴のid>/report/?next=<今のページのパスとクエリ>`へ遷移する。編集者のIDは、画面にもリンクにも出さない（`/editor/<id>/`・編集者の表示名を含まない） |
| 公開・強制公開・自分の編集者の履歴に報告リンクは無い（#1294） | `is_open=True`・`is_open=False`かつ`is_forced_open=True`・自分のIPで`is_open=False`の編集者の履歴 | `class="history-report"`も「編集者: 非公開」も含まない（編集者のページへリンクする） |
| 報告後のトースト（#1294） | `?toast=report` | 「報告しました。ご協力ありがとうございます。」を表示するスクリプトを含む。`toast`が無ければ含まない |

#### 7-10-1. `EditorView` (`/editor/<id>/`)（#991でauthor向けHistory表示を追加、#954で履歴の検索を追加）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在するeditor | 有効なeditor_id | HTTP 200 |
| author向けHistory | `History.create_for_author()`で作成したHistoryが存在 | 作者名が表示され、「この曲は削除されました」は表示されない |
| ユーザーが削除した曲のHistory（#1239） | `is_removed=True`の曲のHistoryが存在 | 曲のページへのリンクは無く「この曲または作者は削除されました」が表示される |
| 本人の判定はX-Real-IP（#1189） | `ip`が`encrypt("203.0.113.1")`のeditor、`X-Real-IP: 203.0.113.1`・`X-Forwarded-For: 198.51.100.1` | `is_me`がTrue |
| X-Forwarded-Forではなりすませない（#1189） | `ip`が`encrypt("203.0.113.1")`のeditor、`X-Real-IP: 203.0.113.2`・`X-Forwarded-For: 203.0.113.1` | `is_me`がFalse（他人のIPを名乗ってその人の編集者になれない） |
| 概要で検索（#954） | titleが「別名を追加」「リンクを編集」のHistoryがあり、`?q=別名` | 「別名を追加」だけが表示され、`total_count`・件数表示は1件。検索フォームに検索語が入る |
| 検索欄のラベル（#954） | 正常アクセス | 検索欄（`input[name="q"]`）に`aria-label="編集履歴の概要で検索"`が付く（編集履歴の一覧と共通の`history_search_form.html`） |
| 他の編集者の履歴は検索結果に含まない（#954） | 別のeditorのHistoryだけが`?q=別名`に一致 | HTTP 200で`total_count`が0（0件と表示） |
| 空白だけの検索語（#954） | `?q=%20%20` | 絞り込まず全件を表示し、`search_query`は空文字 |
| 検索語のエスケープ（#954） | `?q="><script>alert(1)</script>` | 検索フォームの`value`はエスケープされ、`<script>`はそのまま出力されない |
| ページ送りで検索語を引き継ぐ（#954） | `?q=別名&追加`（`&`を含む）で検索結果が`HISTORIES_PER_PAGE`件を超える | 「次へ」が`?page=2&q=<URLエンコードした検索語>`、2ページ目の「前へ」が`?page=1&q=<同>`へのリンクになる。検索結果の件数（`total_count`）は一致したHistoryのみ |
| 検索語が無いときのページ送り（#954） | `HISTORIES_PER_PAGE`件を超える履歴、`q`なし | リンクは`?page=2`のみで`q`を付けない |
| 非公開の編集者（#954） | `is_open=False`で本人以外のアクセス、`?q=別名` | 「この編集者の情報は非公開です。」を表示し、検索フォームも履歴も表示しない |
| 非公開の編集者には報告ボタンだけある（#1291） | `is_open=False`で本人以外のアクセス | 履歴の操作ボタン（再読み込み等）は無く、`.action-buttons`内に報告のページへ遷移する`id="editor-report"`の「報告」リンクだけがある。「この編集者の情報は非公開です。」は表示したまま |
| 報告ボタン（#1291） | 他人の編集者のページ | `.action-buttons`内に`id="editor-report"`の「報告」リンクがあり、`/editor/<id>/report/`へ遷移する |
| 自分のページに報告ボタンは無い（#1291） | `is_me`がTrue | `id="editor-report"`が無い |
| 報告後のトースト（#1291） | `?toast=report` | 「報告しました。ご協力ありがとうございます。」を表示するスクリプトを含む。`toast`が無ければ含まない |

#### 7-10-2. `SongHistoryView` (`/songs/<id>/history/`)

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 存在する曲 | 有効なsong_id | HTTP 200 |
| 存在しない曲 | `song_id=99999` | HTTP 404 |
| ユーザーが削除した曲（#1239） | `is_removed=True` の曲 | HTTP 410で、曲の情報を表示せず、削除を取り消すボタンのあるページ（`song_removed.html`、7-7-2）を表示する（履歴は編集履歴の一覧で見られる） |
| 編集の差分の表示（#608） | 編集（`changes`の見出しが`["種類", "編集前", "編集後"]`）と新規作成（見出しが`["種類", "内容"]`）のHistoryが存在 | `<table class="diff-table">`が編集のHistoryの分だけ（1つ）含まれ、差分を表示する`subekashi/js/editor.js`が読み込まれる |
| 削除の取り消しの履歴（#1264、#1275） | 曲を削除してから、理由を入力して取り消す | HTTP 200で「<タイトル>の削除を取り消し」が表示される。変更内容の表（`change-table-wrapper`）は、削除と取り消しの理由の表（`delete-table`）の2つで、どちらの理由も表示する |
| 理由なしの取り消しの履歴（#1275） | 理由を入力しなかった頃の取り消しのHistory（`history_type="restore"`・`changes=None`） | HTTP 200で「<タイトル>の削除を取り消し」が表示され、変更内容の表（`change-table-wrapper`）は表示しない |
| 非公開の編集者の履歴に報告リンク（#1294） | `is_open=False`の編集者の履歴 | `/histories/<履歴のid>/report/?next=<曲の履歴のパス>`へ遷移する`a#history-report-<履歴のid>`がある。編集者のIDは、画面にもリンクにも出さない |
| 報告後のトースト（#1294） | `?toast=report` | 「報告しました。ご協力ありがとうございます。」を表示するスクリプトを含む。`toast`が無ければ含まない |

#### 7-10-3. `EditorReportView` (`/editor/<id>/report/`)（#1291）

編集者のページの「報告」ボタンから、荒らしを管理者に報告する。報告はDBに保存せず、`CONTACT_DISCORD_URL`のDiscordに送る。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| GET: 報告のフォーム | 他人の編集者のGET | HTTP 200。`form#editor-report-form`（`action`は報告のURL、`POST`）に、必須の`textarea[name=reason]`とCSRFトークンがあり、「戻る」リンクは編集者のページへ遷移する |
| noindex | GET | `<meta name="robots" content="noindex, nofollow">`を含む |
| 送信ボタンは報告理由が空の間は無効 | GET | `input#report-submit`（`type="submit"`）に`disabled`が付き、入力に合わせて有効にする`subekashi/js/editor_report.js`を読み込む（空白だけの間も無効。送信に失敗して理由が残っているときは、開いたときに有効にする） |
| 存在しない編集者 | `editor_id=99999`にGET・POST | どちらもHTTP 404で、Discordに送らない |
| 非公開の編集者も報告できる | `is_open=False`の編集者にGET・POST | GETはHTTP 200、POSTは`/editor/<id>/?toast=report`へリダイレクトし、Discordに管理画面のURLを送る。戻った非公開のページでもトーストを表示する |
| BANされた報告者は報告できない（#1281、#1291） | `is_banned=True`の編集者のIPで、`Referer`付きで報告のページにPOST | `BannedEditorMiddleware`が止め、報告のページへ`?toast=banned`を付けて303でリダイレクトする。Discordに送らない |
| 自分自身は報告できない | 自分の編集者（`ip`が`encrypt(自分のIP)`）にGET・POST | どちらも編集者のページへリダイレクトし、Discordに送らない |
| POST: 正常な報告理由 | `reason="..."`（`send_discord`をモック） | `/editor/<id>/?toast=report`へリダイレクト |
| POST: Discordへの通知 | 同上 | `CONTACT_DISCORD_URL`宛に、理由・報告された編集者の管理画面のURL（`ROOT_URL` + `admin:subekashi_editor_change`）・報告した人の暗号化したIP（`encrypt(IP)`）を含む文面を1回送る。暗号化していないIPは含まない |
| 報告した人のIPはX-Real-IP（#1189） | `X-Real-IP`と、別のIPの`X-Forwarded-For` | 文面の報告した人のIPは`X-Real-IP`のもの（`X-Forwarded-For`のIPでなりすませない） |
| POST: DBは変えない | 正常な報告 | `Editor`が増えず、`History`も作らない |
| POST: 報告理由が空 | `reason=""`・`"  "`・`reason`なし | HTTP 200、`context["error"] == "報告理由を入力してください。"`で、エラーのトーストを表示する。Discordに送らない |
| POST: 報告理由が長すぎる | `reason="あ" * 1001` | HTTP 200、`context["error"] == "報告理由は1000文字以内で入力してください。"`で、入力した理由を残す。Discordに送らない |
| POST: Discordに送信できない | `send_discord`が`False`を返す | 報告はDiscordにしか残らないため、完了にせずHTTP 200で「報告を送信できませんでした。時間をおいて再度お試しください。」のトーストを表示し、入力した理由を`textarea`に残す |
| 報告理由のエスケープ | `reason="</textarea><script>alert(1)</script>"`でDiscordに送信できない | `<script>alert(1)</script>`はそのまま出力されず、エスケープして`textarea`に戻る |

#### 7-10-4. `HistoryReportView` (`/histories/<id>/report/`)（#1294）

履歴一覧・曲の履歴の「編集者: 非公開」の「報告」から、その履歴の編集者を報告する。編集者のIDが画面・URLに出ると、同じIDの履歴どうしが同じ非公開の編集者のものだと分かってしまう（APIが非公開の編集者を`null`にするのはこれを防ぐため）ため、履歴から編集者を引き、編集者のIDを出さない。報告のフォーム・理由の検証・Discordへの送信は`EditorReportView`（7-10-3）と共通（`BaseEditorReportView`）。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| GET: 報告のフォーム | `is_open=False`の編集者の履歴、`?next=/histories/?page=2` | HTTP 200。`form#editor-report-form`（`action`は履歴の報告のURL、`POST`）に、`next`のhidden・必須の`textarea[name=reason]`・CSRFトークン・無効の送信ボタンがあり、対象の編集（履歴のタイトル）を表示する。「戻る」リンクは`next`へ遷移する。`noindex` |
| 編集者のIDを出さない | GET、理由が空・1001文字・Discordに送信できないPOST | どの画面も、`/editor/<id>`・編集者の表示名（`全て<id>の所為です。`）を含まない |
| 存在しない履歴 | `history_id=99999`にGET・POST | どちらもHTTP 404で、Discordに送らない |
| 自分の履歴は報告できない | 自分のIPの編集者の履歴にGET・POST | どちらも`next`へリダイレクトし、Discordに送らない |
| POST: 正常な報告理由 | `reason="..."`、`next=/histories/?page=2`（`send_discord`をモック） | `/histories/?page=2&toast=report`へリダイレクト |
| POST: Discordへの通知 | 同上 | `CONTACT_DISCORD_URL`宛に、理由・報告された編集者の管理画面のURL（`admin:subekashi_editor_change`）・報告された編集の管理画面のURL（`admin:subekashi_history_change`）・報告した人の暗号化したIP（`encrypt(IP)`）を含む文面を1回送る。暗号化していないIPは含まない |
| 報告した人のIPはX-Real-IP（#1189） | `X-Real-IP`と、別のIPの`X-Forwarded-For` | 文面の報告した人のIPは`X-Real-IP`のもの |
| 公開の編集者の履歴も報告できる | `is_open=True`の編集者の履歴にPOST | 非公開の場合と同じく`next`へ`toast=report`を付けてリダイレクトし、その編集者の管理画面のURLを送る |
| `next`はこのサイトのURLだけ | `/songs/5/history/?page=2`・`/histories/?toast=report&q=a`・`/histories/?q=報告`・`http://testserver/histories/`・`https://evil.example/`・`//evil.example/`・`javascript:alert(1)`・空 | このサイトのURLは、`toast`を置き換えて（`/histories/?q=a&toast=report`）元のクエリを残す。他のサイト・不正なURL・空は`/histories/?toast=report`へ戻す |
| `next`のほかのクエリ・フラグメントは変えない | `/histories/?q=a&page=2#top`・`?q=&page=2`（空の値）・`?tag=a&tag=b`（同じキーの繰り返し）・`?toast=old&q=a&toast=older#top`・`/histories/#top` | `toast=report`を末尾に1つだけ付け、元のクエリの順・空の値・繰り返しとフラグメントを残す。元の`toast`は全て置き換える（`/histories/?q=a&toast=report#top`） |
| GET: 安全でない`next` | `?next=https://evil.example/` | 「戻る」リンクと`next`のhiddenは`/histories/` |
| POST: DBは変えない | 正常な報告 | `Editor`・`History`が増えない |
| POST: 報告理由が空・長すぎる | `reason=""`・`"あ" * 1001` | HTTP 200、`context["error"]`にエラーメッセージ。`next`のhiddenを残し、Discordに送らない |
| POST: Discordに送信できない | `send_discord`が`False`を返す | HTTP 200でエラーを表示し、入力した理由と`next`を残す |
| BANされた報告者は報告できない（#1281） | `is_banned=True`の編集者のIPで、`Referer`付きでPOST | `BannedEditorMiddleware`が止め、`?toast=banned`を付けて303でリダイレクトする。Discordに送らない |

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
| `imitate` の指定（#1241） | `imitate=<曲ID>` | 「模倣元が有効です」が含まれる |
| `categorys` の絞り込み（#423） | カテゴリが曲・アレンジ・音MADの曲が存在、`categorys=arrange,otomad` | 「カテゴリが有効です」「3件中2件ヒットしました」が含まれ、アレンジ・音MADの曲のカードのみが返される |
| `categorys` の「以外」（#423） | カテゴリが曲・アレンジの曲が存在、`categorys=~song` | 「カテゴリが有効です」「2件中1件ヒットしました」が含まれ、アレンジの曲のカードのみが返される |

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
| X-Forwarded-Forでは回避できない | 同じ`X-Real-IP`で`X-Forwarded-For`を毎回変えて3回GET | 3回目は429（`X-Forwarded-For`はクライアントが自由に付けられるため使わない） |
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
| 1度でも模倣されたことのある作者数（#1163） | 原曲の作者と、その原曲を模倣した曲の作者が存在 | `stats_items`の「模倣された作者数」は原曲の作者のみの1になり（「総作者数」は2）、レスポンスに「模倣された作者数」が含まれる |
| 模倣された作者数はsongrangeフィルターに連動（#1163） | すべあな界隈曲と界隈外曲の両方が1つの模倣曲に模倣されている、`?songrange=xx` | 「模倣された作者数」は界隈外曲の作者のみの1になる |
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
| グラフに模倣された作者数が渡される（#1163） | `total_imitated_authors`が2・5の2か月分の`Stats`が存在 | `context["monthly_stats"]`の`total_imitated_authors`が`[2, 5]`、月ごとの差分`total_imitated_authors_delta`が`[2, 3]`になる |
| グラフの差分は絞り込み前の全期間から計算（回帰） | `?year=2025`指定、2024年12月と2025年1月の`Stats`が存在 | 表示範囲を2025年のみに絞り込んでも、`song_count_delta`は2024年12月との差分として正しく計算される |
| year選択肢は選択中のsongrangeに連動（回帰、コードレビュー指摘対応） | `?songrange=subeana`、xx曲のみの年とsubeana曲のみの年が混在 | `year_choices`にxx曲のみの年が含まれず、選択しても0件になる組み合わせを避けられる |
| メニューからの導線 | トップページのGET | `/stats/`へのリンクが記事とお問い合わせの間に含まれる |
| `highlighted_month`はyearのみ指定時はNone | `?year=2024`（monthは指定しない） | `context["highlighted_month"]`が`None` |
| `highlighted_month`はmonthのみ指定時もNone | `?month=1`（yearは指定しない） | `context["highlighted_month"]`が`None` |
| `highlighted_month`はyear・month両方指定時のみセット（コードレビュー指摘対応） | `?year=2024&month=6` | `context["highlighted_month"]`が`6`になり、JS側で棒グラフのその月だけ色を変えるための`highlighted-month-data`が埋め込まれる（グラフ側はmonthを無視してその年全体を表示するため、選択していた月をハイライトして元のフィルターとの対応を分かりやすくする） |
| グラフ表示設定はcookie未設定時デフォルト（#1111） | cookie無し | `context["chart_mode"]`が`"monthly"`、`context["chart_series"]`が`"song_count"`になり、対応するラジオボタンに`checked`が付く |
| グラフ表示設定はcookieの値を反映（#1111） | `stats_chart_mode=cumulative`・`stats_chart_series=total_view`のcookieを送信 | `context["chart_mode"]`が`"cumulative"`、`context["chart_series"]`が`"total_view"`になり、対応するラジオボタンのみに`checked`が付く |
| グラフの系列に模倣された作者数を選べる（#1163） | `stats_chart_series=total_imitated_authors`のcookieを送信 | `context["chart_series"]`が`"total_imitated_authors"`になり、`chart-series-total-imitated-authors`のラジオボタンのみに`checked`が付く |
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
| 画面遷移のボタンはhref付きのa | 曲のページ | 「編集/削除」「編集履歴」が`<a href="..." class="action-button">`になる |
| 画面遷移のボタン（黒）はhref付きのa | 別名削除ページ | 「キャンセル」が`<a href="/authors/<id>/aliases/" class="action-button black-action-button">`になる |
| 編集履歴の操作ボタンはbutton | 編集履歴一覧・編集者・曲の編集履歴の各ページ | 「再読み込み」「全て開く/閉じる」が`<button type="button" id="history-reload" class="action-button">`・`<button type="button" id="history-open-all" class="action-button">`になる |
| 別名一覧の再読み込みボタンはbutton | 別名一覧ページ | `<button type="button" id="alias-reload" class="action-button black-action-button">`になる |
| 歌詞の作成結果のボタンはbutton | 歌詞の作成結果ページ | 「最高の行をコピー」「再作成」が`<button type="button" id="copy" class="action-button">`・`<button type="button" id="regenerate" class="action-button">`になる |
| メンテナンス画面の再読み込みボタンはbutton | `IS_MAINTENANCE=True`（`_load_maintenance`をモック）で`/ai/result/`にアクセス | `maintenance.html`が使われ、`<button type="button" id="maintenance-reload" class="action-button">`（文言は`<span>再読み込み</span>`）になる |

#### 7-17. `SettingView` (`/setting/`)（#1164）

検索画面のセクションの「フォームボタン」（`form_button`）で、検索画面のフォームを切り替えるラジオボタン（`#search-form-radios`）を「アイコンのみ」（`icon`）か「アイコンと文字」（`icon_text`、デフォルト）にできる。「アイコンのみ」の場合は`#search-form-radios`に`icon-only`クラスを付け、`css/components/search_form.css`でラベルの`::before`（丸）と`.icon-p-big`（文字）を非表示にする。文字は読み上げでラジオボタンの名前として使われるよう、`display: none`ではなく見えない状態にする。並び替え等のフォーム内のラジオボタンや、検索フォーム以外のラジオボタンには影響しない（トップ画面の「全て表示」の検索フォームにも反映される）。見た目はDjangoテストでは確認できないため、Playwrightで確認する。

トップ画面のセクションの「検索の表示」（`is_shown_search`）は「全て表示」（`all`）・「キーワードのみ」（`on`）・「非表示」（`off`）から選べる（#585）。以前の「表示」の設定を引き継ぐため、「キーワードのみ」の値は`on`とする。

トップ画面のセクションの「初心者向け案内の表示」（`is_shown_guide`）は「表示」（`on`）・「非表示」（`off`）から選べる（#1236）。トップ画面の「表示しない」ボタンで閉じると`off`になり、ここで再び表示できる。トップ画面では`off`以外の値を表示とするため、不正な値の場合も「表示」を選択する。

表示設定のセクションの「フォント」（`font`）は、サイト全体のフォントを「源全ゴシック」（`imitate`、デフォルト）か「k8x12S」（`k8x12s`、ドットフォント）から選べる（#584）。cookieの値は`context_processors`で検証し、許可されていない値は`imitate`とする。値は全てのページの`<html>`の`data-font`に入り、`common.css`の`:root[data-font="k8x12s"]`が`--font-family-main`を切り替える。`html`・`input`・`select`・`option`・`textarea`・ボタン・ヘッダーのロゴ（`.mainfont`）は`--font-family-main`を使う。`@font-face`は使われるまで読み込まれないため、選ばれていないフォントは読み込まない（k8x12sを選ぶと、約3MBの源全ゴシックは読み込まない）。設定画面では、選択するとリロードせず`<html>`の`data-font`を書き換えて、この画面にも反映する。`.sansfont`（`Noto Sans JP`・太字に固定）は、k8x12sを選んでいるときは無効になり（`:where(:root:not([data-font="k8x12s"])) .sansfont`。詳細度は`.sansfont`のまま）、`--font-family-main`で表示する。曲が疑問視されているページ（`is_questionable`）のフォントは、設定に関わらず変わらない。見た目とフォントの読み込みはDjangoテストでは確認できないため、Playwrightで確認する。

Google検索のセクションの「ニュースの提供元」は、当サイトをGoogleの優先するソース（Google検索のトップニュースで優先して表示するサイト）に追加するGoogleのページへのリンクを表示する（#1151）。設定はGoogleのアカウントに保存されるため、cookieには保存しない。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 正常アクセス | GETリクエスト | HTTP 200 |
| 検索の表示の設定のデフォルト（#585） | cookie無し | 「検索の表示」の`<select id="is_shown_search">`が表示され、選択肢は「全て表示」（`all`）・「キーワードのみ」（`on`）・「非表示」（`off`）の順で、「キーワードのみ」が選択される |
| 検索の表示の設定のcookieを反映（#585） | `is_shown_search`に`all`・`on`・`off`のcookieを送信 | それぞれ「全て表示」・「キーワードのみ」・「非表示」のみが選択される |
| 投稿予定の表示の設定のデフォルト（#376） | cookie無し | 「投稿予定の表示」の`<select id="is_shown_upcoming">`がトップ画面のセクションの「新着の表示」の次に表示され、選択肢は「15曲表示」・「10曲表示」・「5曲表示」・「非表示」（`15`・`10`・`5`・`0`）の順で、「5曲表示」が選択される |
| 投稿予定の表示の設定のcookieを反映（#376） | `is_shown_upcoming`に`15`・`10`・`5`・`0`のcookieを送信 | それぞれ「15曲表示」・「10曲表示」・「5曲表示」・「非表示」のみが選択される |
| 初心者向け案内の表示の設定のデフォルト（#1236） | cookie無し | 「初心者向け案内の表示」の`<select id="is_shown_guide">`がトップ画面のセクションの「ネタ曲の表示」の次に表示され、選択肢は「表示」（`on`）・「非表示」（`off`）の順で、「表示」が選択される |
| 初心者向け案内の表示の設定のcookieを反映（#1236） | `is_shown_guide`に`off`・`on`・`<script>`のcookieを送信 | それぞれ「非表示」・「表示」・「表示」のみが選択される |
| フォントの設定のデフォルト（#584） | cookie無し | 表示設定に「フォント」の`<select id="font" class="setting-input">`が表示され、選択肢は「源全ゴシック」（`imitate`）・「k8x12S」（`k8x12s`）の順で、「源全ゴシック」が選択される |
| フォントの設定のcookieを反映（#584） | `font`に`imitate`・`k8x12s`・`<script>`のcookieを送信 | それぞれ「源全ゴシック」・「k8x12S」・「源全ゴシック」のみが選択される |
| フォームボタンの設定のデフォルト | cookie無し | 「フォームボタン」の`<select id="form_button">`が表示され、選択肢は「アイコンのみ」（`icon`）・「アイコンと文字」（`icon_text`）の順で、「アイコンと文字」が選択される |
| フォームボタンの設定のcookieを反映 | `form_button=icon`のcookieを送信 | 「アイコンのみ」が選択される |
| チュートリアルのアイコン | GETリクエスト | 選択肢の保存のチュートリアル（`data-tutorial="select"`）のアイコンは「検索の選択肢の保存」にのみ付き、「フォームボタン」には付かない |
| Googleの優先するソースへのリンク（#1151） | GETリクエスト | 「Google検索」のセクションに、`https://www.google.com/preferences/source?q=lyrics.imicomweb.com`へのリンクが`target="_blank" rel="noopener noreferrer"`付きの`action-button black-action-button`で表示される |

#### 7-18. `SaveSettingsView` (`/api/setting/save/`)（#1164）

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| フォームボタンの設定の保存 | `{"cookies": {"form_button": "icon"}}`・`{"cookies": {"form_button": "icon_text"}}` | HTTP 200、`form_button`のcookieが送信した値で保存される |
| 許可されていない値は保存しない | `{"cookies": {"form_button": "text"}}`・`{"cookies": {"form_button": "<script>"}}` | HTTP 200、`form_button`のcookieは保存されない |
| 検索の表示の設定の保存（#585） | `{"cookies": {"is_shown_search": "all"}}`・`"on"`・`"off"` | HTTP 200、`is_shown_search`のcookieが送信した値で保存される |
| 検索の表示の設定の許可されていない値は保存しない（#585） | `{"cookies": {"is_shown_search": "keyword"}}`・`{"cookies": {"is_shown_search": "<script>"}}` | HTTP 200、`is_shown_search`のcookieは保存されない |
| 投稿予定の表示の設定の保存（#376） | `{"cookies": {"is_shown_upcoming": "0"}}`・`"5"`・`"10"`・`"15"` | HTTP 200、`is_shown_upcoming`のcookieが送信した値で保存される |
| 投稿予定の表示の設定の許可されていない値は保存しない（#376） | `{"cookies": {"is_shown_upcoming": "3"}}`・`"on"`・`"<script>"` | HTTP 200、`is_shown_upcoming`のcookieは保存されない |
| 初心者向け案内の表示の設定の保存（#1236） | `{"cookies": {"is_shown_guide": "on"}}`・`"off"` | HTTP 200、`is_shown_guide`のcookieが送信した値で保存される |
| 初心者向け案内の表示の設定の許可されていない値は保存しない（#1236） | `{"cookies": {"is_shown_guide": "hidden"}}`・`{"cookies": {"is_shown_guide": "<script>"}}` | HTTP 200、`is_shown_guide`のcookieは保存されない |
| フォントの設定の保存（#584） | `{"cookies": {"font": "imitate"}}`・`"k8x12s"` | HTTP 200、`font`のcookieが送信した値で保存される |
| フォントの設定の許可されていない値は保存しない（#584） | `{"cookies": {"font": "k8x12"}}`・`{"cookies": {"font": "<script>"}}` | HTTP 200、`font`のcookieは保存されない |
| 保存したフォントを`<html>`に反映（#584） | cookie無し、`font=k8x12s`のcookie（トップ・曲の検索・設定の各ページ）、`font`に`"><script>alert(1)</script>`のcookie | それぞれ`<html lang="ja" data-font="imitate">`・`data-font="k8x12s"`・`data-font="imitate"`になり、不正な値のスクリプトは出力されない |
| ヘッダーのロゴはフォントの設定に合わせる（#584） | トップ画面のGET | ロゴの文言のリンクは`class="mainfont"`で、旧クラス名の`imitatefont`は含まれない |

#### 7-19. `robots` (`/robots.txt`)（#1172）

`subekashi/static/subekashi/robots.txt`の内容を、`/static/`へリダイレクトせず`/robots.txt`で直接返す。robots.txtの`Disallow`は完全なURLではなくパス（`/`から始まる値）で書かないとどのURLにもマッチしない。Disallowが巡回を制限するかの判定は、`*`を任意の文字列とみなした前方一致で行う。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| robots.txtを直接返す | GETリクエスト | HTTP 200、`Content-Type`が`text/plain; charset=utf-8`で、`User-agent: *`とSitemapの行が含まれる |
| Disallowの値はパス | GETリクエスト | `Disallow`の行が1つ以上あり、全ての値が`/`から始まる |
| Disallowが対象のページにマッチする | 曲の編集・曲の削除・編集者・履歴の報告（`/histories/<id>/report/`、#1294）・設定の各ページのパス | いずれかの`Disallow`にマッチする（履歴の報告は、全ての履歴に報告リンクが出るため、巡回を制限する） |
| Disallowが対象外のページにマッチしない | トップ・曲の検索・曲・曲の編集履歴・編集履歴の一覧（#1294）の各ページのパス | どの`Disallow`にもマッチしない |

#### 7-19-1. `sitemap` (`/sitemap.xml`)（#834）

sitemap.xmlは本番で`const`コマンド（`sitemap`コマンドと`collectstatic`）により起動中に再生成される。`static()`が返すハッシュ付きのファイル名は起動時に読み込んだmanifestから決まり、再生成後も古いファイルを指したままになるため、`static()`を使わずハッシュなしのURLへリダイレクトする。本番と同じ`ManifestStaticFilesStorage`にし、一時ディレクトリの`STATIC_ROOT`に置いたmanifest（`staticfiles.json`）にハッシュ付きのファイル名を持たせて確認する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| ハッシュなしのURLへリダイレクト | manifestに`subekashi/sitemap.xml`のハッシュ付きのファイル名がある状態で`/sitemap.xml`にGET | `{ROOT_URL}/static/subekashi/sitemap.xml`へリダイレクト |

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

#### 7-22. faviconとweb app manifest（#1171）

faviconの画像は`icon_large.png`（800×800）から生成する。`site.webmanifest`の`icons`の`src`はmanifestのURL（`/static/subekashi/`）からの相対パス。本番では`ManifestStaticFilesStorage`がmanifestをハッシュ付きのファイル名で配信するが、manifestの中のパスは書き換えないため、`collectstatic`が残すハッシュなしの画像を参照する。ブラウザがfaviconやmanifestを読み込めるかはDjangoテストでは確認できないため、Playwrightで確認する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| /favicon.icoのリダイレクト | `/favicon.ico`にGET | `/static/subekashi/image/favicon.ico`へリダイレクト |
| 本番では/favicon.icoからハッシュ付きのURLへリダイレクト（#834） | 本番と同じ`ManifestStaticFilesStorage`にし、manifestに`subekashi/image/favicon.ico`のハッシュ付きのファイル名がある状態で`/favicon.ico`にGET | `static()`で、base.htmlの`<link rel="icon">`と同じハッシュ付きのURL（`/static/subekashi/image/favicon.<hash>.ico`）へリダイレクト |
| favicon.icoのサイズ | `favicon.ico` | 16×16・32×32・48×48の3つのサイズを含む |
| apple-touch-iconのサイズ | `apple-touch-icon.png` | 180×180 |
| base.htmlのlinkタグ | トップページ | `rel="icon"`（`sizes="16x16 32x32 48x48"`）・`rel="apple-touch-icon"`（`sizes="180x180"`）・`rel="manifest"`の`<link>`が含まれ、`shortcut icon`は含まれない |
| manifestの内容 | `site.webmanifest` | `name`が`全て歌詞の所為です。`、`short_name`が`すべかし`、`theme_color`が`#000000`、`background_color`が`#111111`で、`icons`の`sizes`が`192x192`・`512x512` |
| manifestのアイコンの画像 | `icons`の各要素 | `src`の画像があり、実際のサイズと形式が`sizes`・`type`と一致する |

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
| `categorys`（#423） | カテゴリがアレンジ・ネタ動画・曲の曲が存在、`?categorys=arrange,meme` | アレンジ・ネタ動画の曲のみ返される（`mediatypes` と同様にカンマ区切りで複数指定できる） |
| `categorys` の「以外」（#423） | カテゴリがアレンジ・ネタ動画・曲の曲が存在、`?categorys=~song,~meme` | 先頭に~を付けたカテゴリの曲を除き、アレンジの曲のみ返される |
| レスポンスの `category`（#423） | `?categorys=song` | 各曲に `category` が含まれる |
| `prush`（#1064） | プレラ「夏プレラ」の曲と「晩夏プレラ6」の曲が存在、`?prush=夏プレラ`・`?prush=プレラ` | 名前の完全一致で絞り込み、「夏プレラ」の曲のみ返される。`?prush=プレラ` では0件（曲ページのタグのリンクで、名前の一部が同じ別のプレラの曲を含めないため） |
| レスポンスの `prush`（#1064） | プレラのある曲と無い曲 | `prush` はidではなくプレラの名前、プレラが無い曲は `null` |
| プレラを曲ごとに取得しない（#1064） | プレラの付いた曲が3件、クエリ無し・`keyword`・`prush` | `FROM subekashi_prush` のクエリが実行されない（`select_related('prush')` で曲と一緒に取得する。`CaptureQueriesContext` で確認） |
| `sort=-imitated_count`（#542） | 曲1が曲2を模倣、`?sort=-imitated_count` | 模倣曲の数が多い曲2、曲1の順で返される |
| ユーザーが削除した曲（#1239） | `is_removed=True`の曲が存在 | 一覧の結果・`count`に含まれない |
| 削除した曲の個別取得（#1239） | `/api/song/<削除した曲のid>/` | HTTP 404 |
| レスポンスの`is_removed`（#1239） | `/api/song/<id>/` | 常にFalseになるため`is_removed`は含まれない。`is_deleted`・`imitateds`・`url`は含まれる |
| 模倣関係の削除した曲（#1239） | `is_removed=True`の曲と模倣関係がある曲を個別取得 | `imitates`・`imitateds`に削除した曲のidが含まれない |

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

#### 8-4-1. `AiAPI` (`PUT /api/ai/<id>/`)（#1256）

**テストクラス**: `AiAPIUpdateTest`（`tests/test_api.py`）

`ai_result.js`は評価した点数を`{"score": n}`だけのPUTで送る。`lyrics`・`genetype`は条件付きの一意制約（`unique_janome_lyrics`）に含まれるため、`AiSerializer`で書き込み可能にしているとDRF 3.18.2以降はモデルの既定値（空文字）が補われ、PUTで上書きされる。`AiSerializer`では読み取り専用にしている。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| scoreだけのPUT | `genetype="janome"`の`Ai`に`{"score": 5}` | HTTP 200、`score`のみ変わり、`lyrics`・`genetype`は変わらない。レスポンスにも`lyrics`が含まれる |
| 同じ歌詞のレガシーレコードがある | 同じ`lyrics`の`genetype="model"`がある状態で、`genetype="janome"`の`Ai`に`{"score": 3}` | HTTP 200、`score`が変わる（一意制約の対象は`genetype="janome"`のみ） |
| 重複したレガシーレコード | 同じ`lyrics`の`genetype="model"`が2件ある状態で、片方に`{"score": 4}` | HTTP 200、`score`が変わる |
| score以外のフィールドを含む | `{"score": 5, "lyrics": "書き換え"}` | HTTP 400、`lyrics`・`score`とも変わらない |

#### 8-5. `SongEditInitView` (`/api/song_edit_init/`)（#1135）

`song_edit.js`は模倣一覧の表示と送信する模倣曲IDのどちらも`imitate_songs`を元にするため、模倣元が1件でも欠けると保存時にその模倣情報が消える。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 模倣元がない曲 | `?song_id=<id>&fetch_imitate=1` | `imitate_songs`が`None`ではなく空配列 |
| 模倣元が検索のデフォルト件数（50件）超 | 模倣元51件の曲 | 51件すべてが返る |
| 削除済み・下書きの模倣元 | `is_deleted=True`・`is_draft=True`の曲を模倣元に持つ曲 | 除外されずにすべて返る |
| ユーザーが削除した模倣元（#1239） | `is_removed=True`の曲と通常の曲を模倣元に持つ曲 | 削除した曲は返らない（保存しても模倣関係は消えない。2-5の`update_song`を参照） |
| プレラを曲ごとに取得しない（#1064） | プレラの付いた模倣元3件と、タイトル・作者が一致するプレラの付いた曲3件 | `imitate_songs`・`title_author_songs`の`prush`はプレラの名前で、`FROM subekashi_prush`のクエリが実行されない（`select_related('prush')`） |
| 存在しないsong_id | `?song_id=99999&fetch_imitate=1` | HTTP 200（500にならない）、`imitate_songs`が`None`（`song_edit.js`は読み込み失敗として登録ボタンを無効化する） |
| 数値でないsong_id | `?song_id=abc&fetch_imitate=1` | HTTP 200（500にならない）、`imitate_songs`が`None` |
| 上付き数字のsong_id | `?song_id=²&fetch_imitate=1` | HTTP 200（500にならない）、`imitate_songs`が`None`（`str.isdigit()`はTrueだが`int()`で変換できない） |
| 範囲外のsong_id | 30桁の数字 | HTTP 200（500にならない）、`imitate_songs`が`None` |

#### 8-5-1. `SongLinkAPI` (`/api/songlink/`)（#1246、#1239）

**テストクラス**: `SongLinkAPITest`（`tests/test_api.py`）

`song_edit.js`・`song_new.js`は、入力したURLが登録済みかをこのAPIで判定する。`url`は`clean_url`で揃えてから検索する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 表記の違うビリビリ動画のURL | `https://bilibili.com/video/BV1qV411J7Kq` の`SongLink`がある状態で、同じURL・`https://www.bilibili.com/video/av417727107/`・`https://m.bilibili.com/video/BV1qV411J7Kq/?spm_id_from=...&p=1` | いずれもその`SongLink`のみを返す |
| 2パート目以降のURL | `https://www.bilibili.com/video/BV1qV411J7Kq?p=2` | 空（別の曲のことがあるため別のURLとして扱う） |
| URLに紐づく曲 | 曲に紐づくURLを`?url=`で指定 | `songs`にその曲が含まれる |
| ユーザーが削除した曲（#1239） | 削除した曲と通常の曲に紐づくURL | `songs`に削除した曲は含まれない |
| 削除した曲だけに紐づくURL（#1239） | 削除した曲だけに紐づくURL | `songs`が空（登録できるURLとして扱われる） |

#### 8-6. スロットリングのIP（`lib/throttling.py`）（#1192）

**テストクラス**: `ApiThrottleClientIPTest`・`ApiThrottleIdentTest`（`tests/test_api.py`）

DRFの既定の`get_ident`は`X-Forwarded-For`の全体を識別子にするため、クライアントが値を変えるだけで制限を回避できる。`subekashi.lib.throttling`の`AnonRateThrottle`・`UserRateThrottle`は`get_ident`を`lib/ip.py`の`get_client_ip`で上書きし、`X-Real-IP`（無ければ`REMOTE_ADDR`）で数える。`ApiThrottleClientIPTest`は`SongAPI`（毎秒2回まで）で確認し、1秒の区切りをまたいでカウントがリセットされないよう、`rest_framework.throttling.SimpleRateThrottle.timer`をモックして時刻を固定する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 1秒に3回目で制限 | 同じ`X-Real-IP`で`/api/song/`に3回GET | 2回目まではHTTP 200、3回目は429 |
| X-Real-IPごとに制限 | IP Aで2回GETした後、IP B・IP AでGET | IP Bは200、IP Aは429 |
| X-Forwarded-Forでは回避できない | 同じ`X-Real-IP`で`X-Forwarded-For`を毎回変えて3回GET | 3回目は429 |
| X-Real-IPが無ければREMOTE_ADDRごとに制限 | `REMOTE_ADDR` Aで2回GETした後、`REMOTE_ADDR` B・AでGET | Bは200、Aは429 |
| 全てのAPIのビューのスロットリング | `subekashi.urls`から集めたDRFのビュー（`APIRootView`・既定の`AnonRateThrottle`を使うビューを含む）の全ての`throttle_classes`で、`REMOTE_ADDR: 10.0.0.1`・`X-Real-IP: 203.0.113.1`・`X-Forwarded-For: 198.51.100.1`のリクエストの`get_ident` | 全て`203.0.113.1`（ビューを追加したときにDRFのクラスをそのまま使っていないかを確認する） |

#### 8-7. `NewsAPIView` (`/api/news/`)（#925）

**テストクラス**: `NewsAPIViewTest`（`tests/test_api.py`）

`X-API-Key`ヘッダーの値が`local_settings.py`の`API_KEY`と一致する場合のみ、トップ画面に表示するニュース（`tag="news"`の`Article`）を登録する。Cookieのセッションでは認証しないため、管理画面にログインしていてもAPIキーが無ければ登録できない。テストでは`override_settings(API_KEY="test-api-key")`で設定する。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 正しいAPIキー | `X-API-Key: test-api-key`、`{"article_id": "testNews", "title": "テストのニュース\n"}` | HTTP 201、`{"article_id": "testNews", "title": "テストのニュース"}`（末尾の改行は除く）。`tag="news"`・`author="全て歌詞の所為です。"`・`is_open=True`・`is_md=True`・`handle_as_news=False`・`post_time`がPOST時刻の記事が作成され、`get_top_news_articles()`に含まれる |
| マークダウンのタイトル | `title="[リンク](https://example.com)が公開される"` | `<a href="https://example.com">リンク</a>が公開される`に変換して保存される |
| CSRFトークンなし | `APIClient(enforce_csrf_checks=True)`で正しいAPIキー | HTTP 201（スクリプトからCSRFトークンなしでPOSTできる） |
| APIキーなし | `X-API-Key`ヘッダーなし | HTTP 403、記事は作成されない |
| 間違ったAPIキー | `X-API-Key: wrong-api-key` | HTTP 403、記事は作成されない |
| 管理画面にログイン済み | スーパーユーザーでログインし、`X-API-Key`ヘッダーなし | HTTP 403、記事は作成されない |
| `API_KEY`が未設定 | `API_KEY=""`、`X-API-Key: `（空文字列） | HTTP 403、記事は作成されない（空文字列同士で一致させない） |
| GET | 正しいAPIキーでGET | HTTP 405 |
| 既存のarticle_id | `tag="blog"`の記事と同じ`article_id` | HTTP 400（`article_id`のエラー）、既存の記事のタイトル・タグ・`post_time`は変わらない |
| 不正なarticle_id | 空文字列・`/`を含む・日本語・101文字 | HTTP 400（`article_id`のエラー）、記事は作成されない |
| タイトルが空 | `title`なし・空白と改行のみ | HTTP 400（`title`のエラー）、記事は作成されない |
| 変換後のタイトルが上限を超える | `title="**a**"×100`（500文字） | HTTP 400（`title`のエラー）、記事は作成されない |

#### 8-8. 公開API（`views/api/open_data.py`・`lib/pagination.py`）（#1243）

**テストクラス**: `OpenDataAPICommonTest`・`OpenDataThrottleTest`・`OpenDataPaginationTest`・`AuthorAPITest`・`PrushAPITest`・`HistoryAPITest`・`ContactAPITest`・`WordAPITest`・`StatsAPITest`・`ArticleAPITest`（`tests/test_api.py`）

誰でもGETで取得できる読み取り専用のAPI。`/api/author/`・`/api/prush/`・`/api/history/`・`/api/contact/`・`/api/word/`・`/api/stats/`・`/api/article/`の一覧と`<id>/`の個別取得。編集者（`Editor`）のAPIは作らない。一覧は曲のAPIと同じく`page`・`size`で範囲を指定し、`count`・`page`・`size`・`max_page`・`result`を返す。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 一覧の形式 | 各APIに`GET` | HTTP 200、キーが`count`・`page`・`size`・`max_page`・`result`の順 |
| GET以外 | 各APIに`POST` | HTTP 405 |
| CORS | `Origin`ヘッダー付きで各APIに`GET` | `Access-Control-Allow-Origin: *`、`Access-Control-Allow-Credentials`は返らない |
| ブラウザで表示するAPIの画面 | `Accept: text/html`で各APIに`GET` | HTTP 200（`django_filters`のテンプレートを読み込めないと500）。`/api/history/`は絞り込みのフォーム（`name="editor"`）を含む |
| 1秒に3回目で制限 | 同じ`X-Real-IP`で`/api/author/`に2回、`/api/history/`に1回`GET` | 3回目はHTTP 429（毎秒2回まで） |
| ページ分割: 既定 | プレラ5件、パラメータなし | `count=5`・`page=1`・`size=50`・`max_page=1`、id順に5件 |
| ページ分割: page・size | `?page=2&size=2` | `max_page=3`、3・4件目 |
| ページ分割: sizeの上限 | `?size=1001` | `size=1000` |
| ページ分割: 不正な値 | `page`・`size`に`abc`・`0`・`-1`・`²`・空文字列 | `page=1`・`size=50` |
| ページ分割: 範囲外のページ | `?page=4&size=2`・30桁の`page` | `count=5`、`result`が空（500にならない） |
| 作者 | 別名・リンクのある作者を個別取得 | `{"id", "name", "aliases": [{"name", "alias_type"}], "links": [URL]}` |
| 存在しない作者 | `/api/author/99999/`・30桁のid | HTTP 404 |
| 作者の別名・リンクを作者ごとに取得しない | 別名・リンクのある作者4人の一覧 | `subekashi_authoralias`・`subekashi_authorlink`のクエリがそれぞれ1回（`prefetch_related`） |
| プレラ | 個別取得 | `{"id", "name", "date"}` |
| 編集履歴 | 曲の編集履歴を個別取得 | `id`・`song`・`author`・`title`・`history_type`・`create_time`・`changes`・`editor`（編集者のid） |
| 非公開の編集者 | `is_open=True`・`is_open=False`・`is_forced_open=True`の編集者の履歴 | `editor`は公開・強制公開の編集者はid、非公開の編集者は`null`（画面の「編集者: 非公開」と同じ） |
| 編集者のIP | 一覧 | レスポンスに編集者の`ip`が含まれない |
| 編集履歴の並び順 | 一覧 | 新しい順 |
| 曲・作者で絞り込み | `?song=<id>`・`?author=<id>` | その曲・作者の履歴のみ |
| 編集者で絞り込み | `?editor=<id>` | 公開・強制公開の編集者はその編集者の履歴、非公開の編集者は空（非公開の編集者の履歴がどれかわからないようにする） |
| 不正な絞り込み | `?editor=abc`・`?song=1.5`・`?author=1e3` | HTTP 400（それぞれの項目のエラー。小数を切り捨ててid=1として絞り込まない） |
| 範囲外のidで絞り込み | `?song=`30桁の数字・30桁の負の数 | HTTP 400（`song`のエラー。SQLiteで扱えない大きさの整数でクエリを実行すると`OverflowError`で500になるため） |
| 編集者を履歴ごとに取得しない | 編集者の違う履歴6件の一覧 | `FROM subekashi_editor`のクエリが実行されない（`select_related`） |
| 問い合わせ | 回答済み・未回答の問い合わせ | 一覧は回答済みのみ（`id`・`detail`・`post_time`・`answer`）。未回答の個別取得はHTTP 404 |
| 模倣単語 | 個別取得 | `id`・`word`・`hinshi`・`katsuyou`・`candidate` |
| 模倣単語の絞り込み | `?word=`・`?hinshi=`・`?hinshi=&katsuyou=` | 完全一致で絞り込む |
| 模倣単語候補のAPI | `/api/word/candidates/`・`/api/word/abc/` | `word-candidates`のまま（個別取得のidは数字に限る）。`/api/word/abc/`はHTTP 404 |
| 統計 | `?songrange=xx` | その`songrange`のみ、年・月の順 |
| 不正なsongrange | `?songrange=invalid` | HTTP 400（`songrange`のエラー） |
| 記事 | 公開済み・非公開・公開日時の前の記事 | 一覧は公開済みのみ、`post_time`の新しい順。非公開・公開日時の前の記事の個別取得はHTTP 404 |
| 「.」を含む記事のid | `/api/article/LiveStreamVol.6/` | HTTP 200 |
| 記事の項目 | 個別取得 | `is_open`は含まれない（常にTrueのため）。`article_id`・`title`・`author`・`tag`・`text`・`post_time`・`is_md`・`handle_as_news`を含む |
| 記事のタグで絞り込み | `?tag=news` | ニュースの記事のみ |

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
| 埋め込みプレイヤーのiframeの許可（#1254） | YouTube・ニコニコ動画・SoundCloud（曲・プレイリスト）・ビリビリ動画・Google Drive・ScratchのURLの`get_embed()`の`src` | `src`のオリジン（`scheme://host`）が`frame-src`に含まれる（無いとCSPでブロックされる） |

#### 9-4. `BannedEditorMiddleware`（#1281）

`Editor.is_banned`がTrueの編集者（`Editor.ip`が`get_ip`の値と一致する）は、ページの読み取り（GET・HEAD・OPTIONS）以外のリクエストができない。サイトの閲覧はできる。以前の`RestrictIPMiddleware`（`ban.py`の`BAN_LIST`にあるIPからのアクセスをすべて500にしていた）の代わりで、`BAN_LIST`から`is_banned`への移行は「11-11」に記載している。ビューごとではなくミドルウェアで判定するため、POSTなどを持つビューが増えても漏れない。止めるときの返し方は、JSからのリクエスト（`/api/`、`Sec-Fetch-Mode`が`navigate`以外のfetch・XHR、`X-Requested-With`、`Accept: application/json`、JSONの`Content-Type`）はJSONの403（HTMLにリダイレクトするとfetchが成功に見えるため）、ブラウザのフォーム送信は送信したフォームのあるページ（`Referer`）に`?toast=banned`を付けて戻す（`base.js`がトーストを表示する）。戻れないときは500のページを表示する。管理サイト（`/admin/`）は止めない（管理者のIPをBANしても、ログインしてBANを解除できるように）。編集者が存在しないIPはBANされていない扱いで、判定のために`Editor`を作らない。テストは`test_middleware.py`の`BannedEditorMiddlewareTest`。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| フォームのPOST | BANされた編集者が、曲の登録・編集・削除・削除の取り消し、別名の追加・編集・削除、名義の統一、お問い合わせ、宣伝のフォームのあるページを`Referer`にしてPOST | HTTP 303で`<Refererのパス>?toast=banned`に戻す。曲・作者・別名・`Ai`・`Ad`・`History`・`Contact`・`SongLink`・`Editor`が変わらず、Discordに送信されない |
| 戻した先のページ | 上記を`follow=True`でPOST | HTTP 200 |
| `Referer`のクエリとフラグメント | 名義の統一の確認ページの`Referer`が`?name=…&toast=unified&name_unified=1&empty=#top`付き | HTTP 303で、戻し先は`name`・`empty`のクエリを残して`toast=banned`を付け、`toast`・`name_unified`・フラグメントは外す |
| クエリが必要なページに戻せる | 名義の統一の確認ページ（`?name=…`が必要）の`Referer`でPOST、`follow=True` | 戻し先の確認ページがHTTP 200（クエリが無いと別名一覧にリダイレクトされてしまう） |
| `Referer`が無い | 上記のフォームを`Referer`なしでPOST | HTTP 500、`500.html`を表示。何も変わらず、Discordに送信されない |
| 他のサイトの`Referer` | `https://example.com/…`・`http://testserver.example.com/…`・`http://testserver@example.com/…`・`//example.com/…`・`javascript:alert(1)` | HTTP 500、`500.html`を表示（外部へリダイレクトしない） |
| 管理サイトの`Referer` | `/admin/…`を`Referer`にしてPOST | HTTP 500、`500.html`を表示（管理サイトのページにはトーストが無い） |
| 管理サイトのPOSTは止めない | BANされた編集者が`/admin/login/`にPOSTしてログインし、管理サイトの編集者の変更画面で`is_banned`を外す | ログインは302、編集者の変更も302で`is_banned`が`False`になる（BANを解除できる） |
| 管理サイトのパスワードの間違い | `/admin/login/`に誤ったパスワードでPOST | HTTP 200（ログイン画面）。`500.html`にはならない |
| JSからのリクエスト | フォームのURLに、`Sec-Fetch-Mode: same-origin`・`Sec-Fetch-Mode: cors`・`X-Requested-With: XMLHttpRequest`・`Accept: application/json`・`Accept: text/plain, application/json;q=0.9`のいずれかを付け、`Referer`付きでPOST | HTTP 403、`{"detail": BANNED_ERROR}`。`Location`は付かず、DBは変わらない |
| JSONのPOST | `Content-Type: application/json`でフォームのURLにPOST | HTTP 403、`{"detail": BANNED_ERROR}` |
| JSからの`Referer`なしのPOST | `Sec-Fetch-Mode: same-origin`で、`Referer`なしでPOST | HTTP 403のJSON（500のページではない） |
| ブラウザのフォーム送信 | `Sec-Fetch-Mode: navigate`・`Accept: text/html,…`で、`Referer`付きと`Referer`なしのそれぞれでPOST | `Referer`付きは303で`?toast=banned`に戻し、`Referer`なしは500のページ |
| APIのPOST・PUT・PATCH・DELETE | 単語の入れ替え、作成歌詞の評価（PUT・PATCH）、宣伝のクリック、設定の保存、公開の設定、ニュースの登録、曲の削除・作成（API）、お問い合わせ（API） | HTTP 403、`{"detail": BANNED_ERROR}`。Cookieを設定せず、DBが変わらず、Discordに送信されない |
| 閲覧はできる | トップ・曲のページ・曲の登録・曲の編集・別名一覧・お問い合わせ・宣伝をGET・HEAD | いずれもHTTP 200 |
| APIのGET・OPTIONS | `/api/song/<id>/`をGET、`/api/song/`をOPTIONS | いずれもHTTP 200 |
| 検索のPOST | `/songs/`にPOST | HTTP 200（検索条件のCookieを保存して検索結果を返すだけで、DBに保存しないため止めない） |
| BANの解除 | `is_banned`を`False`にして曲の登録をPOST | HTTP 302で曲が登録される |
| 別の編集者のBAN | 別のIPの編集者だけがBANされている状態で曲の登録をPOST | HTTP 302で曲が登録される |
| 編集者が無いIP | `Editor`が存在しないIPからPOST | ビューを呼び出し、`Editor`を作らない |
| ビューを呼ばない | BANされた編集者のPOST・PUT・PATCH・DELETE・TRACE（`RequestFactory`） | `get_response`を呼ばず、HTTP 303を返す |
| 読み取りはビューを呼ぶ | BANされた編集者のGET・HEAD・OPTIONS（`RequestFactory`） | `get_response`を呼ぶ |
| トーストの文言をdata属性で渡す | トップ・曲の登録・存在しないページをGET、`base.js` | `<body>`に`data-banned-message="<BANNED_ERROR>"`が出る。`base.js`は`document.body.dataset.bannedMessage`を読み、文言を直書きしない（`BANNED_ERROR`と二重管理しない） |
| CSRFトークンが無くてもBANとして止める | CSRFの検証を有効（`enforce_csrf_checks=True`）にして、BANされた編集者がトークン無し・誤ったトークン・正しいトークンでPOST | どれも`Referer`付きは303、JS（`Sec-Fetch-Mode: same-origin`）は403のBANのJSON、`Referer`なしは500のページ。CSRFの失敗（403のHTML）にならない（`CsrfViewMiddleware`の検証は`process_view`で、ミドルウェアの`__call__`より後に動くため） |
| BANされていない編集者のCSRFの検証は変わらない | 同じ設定で、BANされていない編集者がトークン無し・正しいトークンでPOST | トークン無しは403のCSRFの失敗（BANの応答ではなく、`Location`も付かない）、正しいトークンは302で曲が登録される |
| X-Real-IPで判定 | `REMOTE_ADDR`は未BAN、`X-Real-IP`はBANされたIP | HTTP 303 |
| X-Forwarded-ForではBANを回避できない | `X-Real-IP`は無く`REMOTE_ADDR`がBANされたIP、`X-Forwarded-For`は別のIP | HTTP 303（#1189） |
| X-Forwarded-ForでBANされたIPを名乗っても制限されない | `REMOTE_ADDR`は未BANのIP、`X-Forwarded-For`がBANされたIP | HTTP 302で曲が登録される（#1189） |

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
| ユーザーが削除した曲は数えない（#1239） | 上記に加え、Dが削除した曲2曲を模倣し、削除した曲2曲がCを模倣する | 数えると順序が変わるが、`-imitate_count` は A, D, C, B、`-imitated_count` は B, C, D, A の順のまま。削除した曲は結果に含まれない |
| 件数の取得では並び替えない（#1124） | `{"keyword": "...", "sort": "-imitated_count", "count": True}` | 件数取得（`COUNT(*)`）のSQLに模倣曲の数のサブクエリと `ORDER BY` が含まれない |

#### 10-9. `lib/song_filterset.py` の `order_by_sort_with_missing_last(queryset, sort)`（作者ページの並び替え、#606）

**テストファイル**: `tests/test_lib_song_filterset.py`

曲の検索ではYouTube関連の並び替えで情報が無い曲を除外する（`SongFilter.qs`）が、作者ページでは除外せず末尾に並べる。末尾に並べる条件は検索の除外条件（`upload_time`がNULL・`view`/`like`が1未満）と同じ定数`YOUTUBE_DATA_CONDITIONS`を使い、片方だけが変わらないようにする。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 投稿日の並び替え | 投稿日なし・2020年・2024年の曲で`upload_time` / `-upload_time` | 2020年→2024年→投稿日なし / 2024年→2020年→投稿日なし |
| 再生回数の並び替え | 再生回数なし・0・10・100の曲で`view` / `-view` | 10→100 / 100→10 の後に、再生回数なし・0の曲が並ぶ |
| 高評価数の並び替え | 高評価数なし・0・5・50の曲で`like` / `-like` | 5→50 / 50→5 の後に、高評価数なし・0の曲が並ぶ |
| 情報が無い曲同士の順序 | YouTubeの情報が無い2曲で`YOUTUBE_SORTS`の各値 | 登録日の遅い順 |
| 同じ値の曲同士の順序 | 再生回数が同じ2曲で`-view` / `view` | どちらも登録日の遅い順 |
| YouTube以外の並び替え | `id` / `-id` | 曲の検索（`order_by_sort`）と同じ順序 |
| 模倣曲の数・模倣元の数 | 模倣元と模倣曲で`-imitated_count` / `-imitate_count` | 模倣元→模倣曲 / 模倣曲→模倣元 |
| ランダム | `random` | 全曲が含まれる |

---

### 11. モデル — 基本動作

**テストファイル案**: `tests/test_models.py`

#### 11-1. `Song` モデル

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| 曲の作成 | `Song.objects.create(title="テスト曲", ...)` | DBに保存される |
| `authors_str()` メソッド | 複数作者を持つ曲 | 作者名がカンマ区切りで返される |
| `is_questionable` のデフォルト値 | フラグ未指定で作成 | `is_questionable == False` |
| `category` のデフォルト値（#423） | カテゴリ未指定で作成 | `category == "song"` |
| カテゴリの選択肢（#423） | `Song.CHOICES` | ネタ動画は `"meme"`（ネタ曲の `is_joke` とは無関係）で、`"joke"` は無い。「その他」（`"other"`）・「解読」（`"dec"`）も無い。`"notice"` の表示名は「予告」 |
| ネタ動画のアイコン（#423） | `SONG_CATEGORIES` のネタ動画・`SONG_FLAGS` のネタ曲 | アイコンが異なる |
| カテゴリの選択肢は `SONG_CATEGORIES` から作る（#423） | `Song.CHOICES` | `SONG_CATEGORIES` の順・表示名と一致し、先頭は `("song", "曲")`。全てのカテゴリにFont Awesomeのアイコンがある |
| `get_category()`（#423） | `category="meme"` の曲 / `category="joke"`（変更前の値）の曲 | `{"value": "meme", "label": "ネタ動画", "icon": "far fa-laugh-squint"}` / `None` |
| マイグレーション `0050_song_category_meme`（#423） | `category="joke"` の曲と `category="song"` の曲に `joke_to_meme` を実行 / `category="meme"` の曲に `meme_to_joke` を実行 | `"joke"` は `"meme"` に変わり、`"song"` は変わらない / `"meme"` は `"joke"` に戻る |
| `is_deleted=True` の曲 | 削除フラグを立てる | DBに残るが削除済みとして扱われる |
| ManyToMany: authors | `song.authors.add(author)` | 作者が曲に紐付く |
| ManyToMany: imitates (自己参照) | `song.imitates.add(other_song)` | 模倣関係が成立する |

#### 11-1-2. ユーザーが削除した曲を除くマネージャー（`SongManager`）（#1239）

`Song.objects`（デフォルトマネージャー）は`is_removed=True`の曲を除き、`Song.all_objects`は全件を返す

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `Song.objects` | 通常の曲と削除した曲 | 通常の曲だけを返す |
| `Song.all_objects` | 通常の曲と削除した曲 | どちらも返す |
| `get_or_none()` | 削除した曲のid | `None`（曲のページ・編集・削除・編集履歴のページは、削除を取り消すボタンのあるページになる） |
| `get_for_author()` | 作者の曲に削除した曲がある | 削除した曲を含まない |
| 関連マネージャー（`author.songs`・`song.imitates`・`song.imitateds`・`link.songs`） | 削除した曲と関連がある | 削除した曲を含まない（デフォルトマネージャーから作られるため） |
| `History.song` | 削除した曲のHistory | 削除した曲を返す（FKの参照はベースマネージャーを使うため。編集履歴の一覧で「削除されました」と表示するのに使う） |
| デフォルトマネージャー | `Song._default_manager` | `objects` |

#### 11-1-1. `Song.get_flags(is_lack=False)`（#1228）

曲ページのタグ・曲カードのアイコンに出すフラグを、`SONG_FLAGS`（`constants/constants.py`）から選んで返す。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| フラグなし | すべてのフラグが既定値 | 空のリストを返す |
| 各フィールドのフラグ | `is_questionable`・`is_draft`・`is_original`・`is_joke`・`is_inst`・`is_deleted`・`is_special`・`is_limited` のいずれかが `True`、または `is_subeana=False` | 対応するフラグ（`is_subeana=False` は `is_xx`）だけを返す |
| 未完成は引数で受け取る | `is_lack=True` を渡す／渡さない | 渡したときだけ `is_lack` のフラグを返す |
| 界隈曲?の非すべあな曲 | `is_questionable=True`・`is_subeana=False` | `is_questionable` だけを返し、`is_xx` は返さない |
| フラグの順番 | 界隈曲?以外のすべてのフラグ・`is_lack=True` | `SONG_FLAGS` と同じ順に返す |

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
| `TransitiveAlias.is_direct_successor`（#1230） | 上記のA〜Eで、C・A・Eの`get_transitive_aliases()` | Cの一覧のA（直接・逆方向・past）だけが`True`。Aの一覧のC・D（正方向のpast）、Eの一覧のA（逆方向のgroup）は`False` |
| `TransitiveAlias.is_direct_successor`・間接的な逆方向のpast（#1230） | newestがmiddleを、middleがoldestをpast別名として登録し、oldestの`get_transitive_aliases()` | middleは`True`。newestは「その後の名称」と表示されるが、直接の関係ではないため`False` |
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
| マイグレーション `0051_songlink_bilibili_url`: URLを揃える（#1246） | `?spm_id_from=` の付いたビリビリ動画のURL・揃えたビリビリ動画のURL・末尾に`/`の付いたニコニコ動画のURLに `normalize_bilibili_urls` を実行 | 1つ目は `https://bilibili.com/video/BV<id>` になり曲の紐付けは残る。2つ目・ニコニコ動画のURLは変わらない |
| マイグレーション `0051_songlink_bilibili_url`: 同じ動画のURLを1つにまとめる（#1246） | BV番号のURL・同じ動画のav番号のURL（`allow_dup=True`）・末尾に`/`の付いたBV番号のURLにそれぞれ別の曲が紐付いている | BV番号のURLの1件だけが残り、3曲とも紐付き、`allow_dup=True`（どちらかがTrueならTrue） |
| マイグレーション `0051_songlink_bilibili_url`: 揃えたURLが無い場合（#1246） | av番号のURL（曲なし）と、末尾に`/`の付いた同じ動画のBV番号のURL（曲あり） | 先に登録したav番号のURLがBV番号のURLになり、もう一方の曲が紐付く。`SongLink`は1件になる |
| マイグレーション `0056_stats_total_imitated_authors`: songrangeごとの累積値（#1163） | 1月にすべあな界隈曲・界隈外曲、2月にすべあな界隈曲（いずれも作者あり）と、2月の模倣曲（上の3曲を模倣）が存在し、1月・2月のall/subeana/xxの`Stats`に `fill_total_imitated_authors` を実行 | 各月の末日までに投稿された曲の作者のうち、模倣された作者数が入る（all: 1月2・2月3、subeana: 1月1・2月2、xx: 1月1・2月1）。模倣曲の投稿が月末より後でも数える |
| マイグレーション `0056_stats_total_imitated_authors`: 12月の月末（#1163） | 12月の曲とその模倣曲が存在し、`year`が12月の`Stats`に `fill_total_imitated_authors` を実行 | 翌年1月1日未満の曲まで含め、1になる |
| マイグレーション `0056_stats_total_imitated_authors`: 削除した曲（#1163） | 削除した曲にのみ模倣されている曲と、削除した曲を模倣している通常の曲が存在 | どちらの作者も数えず、0になる |
| マイグレーション `0056_stats_total_imitated_authors`: lib側と同じ結果（#1163） | 共作曲とその模倣曲2曲が存在 | `compute_common_stats`の`total_imitated_authors`と同じ値になる（`compute_imitated_author_count`をコピーした処理のずれを防ぐ） |
| マイグレーション `0051_songlink_bilibili_url`: `is_removed`（#1246） | 削除された曲のURL（`is_removed=True`）と、同じ動画の曲に紐付くURL / 両方とも削除された曲のURL | `is_removed=False`（曲に紐付くURLが「削除された曲のURL」として編集できなくならないように） / `is_removed=True` |

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
| デフォルト値 | `year`・`month`のみ指定して作成 | 各集計フィールド（`total_imitated_authors`を含む、#1163）が`0`になる |
| `songrange`のデフォルト値 | `year`・`month`のみ指定して作成 | `songrange`が`"all"`になる |
| `(year, month, songrange)`のユニーク制約 | 同じ`year`・`month`・`songrange`で2件作成 | `IntegrityError`が発生 |
| `songrange`が異なれば同じ`(year, month)`でも作成可能 | `songrange="all"`と`songrange="subeana"`で同じ`(year, month)` | 2件とも作成できる |
| `__str__` | `year=2026, month=3, songrange="all"` | `"2026-03 (all)"` |
| `get_monthly_series()`の並び順 | 複数月のレコードを順不同で作成 | `year`, `month`昇順で返る |
| `get_monthly_series(songrange)`の絞り込み | `songrange="all"`と`songrange="subeana"`のレコードが混在 | 指定した`songrange`のレコードのみ返る |

---

#### 11-9. `Prush` モデル（#1064）

プレラ（プレミアラッシュ）。すべあな界隈年表のプ列から `timeline` コマンドで登録し、`Song.prush`（null可の外部キー）で曲に1つだけ付ける。新規登録・編集画面からは登録・編集できない。`date` は年表でそのプレラが最初に出てくる行の日付で、曲の検索の選択肢を新しい順に並べ、年ごとに分けるのに使う（マイグレーション `0053_prush`）。

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `__str__` | `Prush(name="年末プレラ５")` | `"年末プレラ５"` |
| `date` のデフォルト値 | 日付を指定せずに作成 | `None` |
| `Song.prush` のデフォルト値 | プレラを指定せずに曲を作成 | `None` |
| プレラの削除 | プレラの付いた曲があるプレラを削除 | 曲は残り、`prush` は `None` になる（`SET_NULL`） |

#### 11-10. `SongTimeline` モデル（#1269）

すべあな界隈年表で曲が載っている行。`timeline` コマンドで保存し（27-3）、曲のページの「年表で見る」「年表に登録する」ボタンに使う。`Song` と1対1で、`year`・`sheet_id`（シートのID、URLのgid）・`row`・`is_lyrics_blank`（URL列で曲に一致した行の歌詞列が空か。空なら曲のページで「年表に登録する」ボタンにする）を持つ（マイグレーション `0055_songtimeline`）。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| `__str__` | `year=2024`・`row=45` | `"2024年45行目"` |
| `is_lyrics_blank` のデフォルト値 | 指定せずに作成 | `False` |
| 曲の削除 | 年表の行がある曲を削除 | 年表の行も削除される（`CASCADE`） |

#### 11-11. `Editor` モデル（#1281）

曲や作者を編集したユーザーのIP（`encrypt`した値）の情報。`is_banned`（デフォルト`False`）が`True`の編集者は、ページの読み取り（GET・HEAD・OPTIONS）以外のリクエストができない（9-4）。以前の`ban.py`の`BAN_LIST`（IPそのもの）の代わりで、管理サイトの編集者の一覧から変更できる。

| テストケース | 操作 | 期待結果 |
| --- | --- | --- |
| `is_banned`のデフォルト値 | 指定せずに作成 | `False` |
| `is_banned_ip(ip)` | `is_banned=True`の編集者・BANされていない編集者・編集者がいないIPを指定 | BANされた編集者のIPのみ`True`。編集者は作られない |

##### 11-11-1. `0057_editor_is_banned`のデータ移行（`ban_listed_editors`）

廃止した`subekashi/constants/dynamic/ban.py`（gitignore対象。本番のサーバーにある）の`BAN_LIST`のIPを`encrypt`し、`Editor.ip`が一致する編集者を`is_banned=True`にする。`ban.py`は`import`せずファイルとして読み、`encrypt`もマイグレーションにコピーしている（`lib/security.py`を後から変えても移行の挙動が変わらないように）。編集者が見つからないIPと、IPとして読めない値は、手作業で確認できるよう`migrate`の出力に出す。編集者は作らない。テストでは`BAN_LIST_PATH`を一時ファイルに差し替える。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| `encrypt`のコピーが本体と同じ | IPv4・`0.0.0.0`・IPv6・`::1`と`SYMBOLS` | `lib/security.py`の`encrypt`・`SYMBOLS`と一致する |
| `BAN_LIST`の編集者をBANにする | IPv4・IPv6の編集者と、`BAN_LIST`にない編集者 | `BAN_LIST`のIPの編集者のみ`is_banned=True`。出力に「BAN_LIST 2件のうち2件の編集者をis_bannedにしました。」 |
| 編集者を特定できないIPとIPとして読めない値の報告 | `BAN_LIST`に、編集者のいるIP・編集者のいないIP・`"not-an-ip"` | 編集者のいるIPのみBAN。出力に「編集者を特定できないIP: …」「IPとして読めない値: not-an-ip」。`Editor`は増えない |
| 重複と空白 | `BAN_LIST`に同じIP（前後に空白あり）・空文字 | 重複と空白を除いて1件として扱う |
| 編集者が1件もない | 編集者なしで`ban.py`あり | 何もせず、何も出力しない（新規構築・テストのDB） |
| `ban.py`がない | 編集者ありで`ban.py`なし | `is_banned`は変わらず、「が無いため」を含むメッセージを出力する |
| `BAN_LIST`が空 | 編集者ありで`BAN_LIST = []` | 何も出力せず、`is_banned`は変わらない |

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
| 記事ごとの`<div>`の対応（#1244） | `howToArticle`・`tag="news"`・`tag="blog"`の記事が存在（ニュースの記事は`setUp`で作成） | 3種類の行がそれぞれ出力され、`#mainarticle`内の`<div>`の開始タグ（`<div[\s>]`）と`</div>`の数が一致する（記事の投稿方法・ニュースで`</div>`が余計に出力されない） |

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
| 画像の拡大表示（#1303） | `is_md=True`で本文に`![画像](...)`を含む | 拡大表示用の`<dialog id="image-viewer">`（`#image-viewer-img`・`#image-viewer-close`を含む）と、`article/js/default_article.js`の`<script defer>`が出力される。クリック（タップ）で開く動作はJSのため、Playwrightで確認する |

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

#### 13-2. `parse_sqlite_id(value)`（#1290）

ASCIIの数字だけで、SQLiteの整数の範囲に収まる文字列を整数にする。変換できなければ`None`を返す（例外にしない）。`SQLiteIntConverter.to_python()`が使うほか、クエリ文字列のidを検証する別名一覧画面（`get_unify_conflict_authors()`）が使う。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 通常の整数 | `"123"` | `123` を返す |
| 0 | `"0"` | `0` を返す |
| SQLite INT最大値 | `str(9223372036854775807)` | そのまま返す |
| 最大値超過 | `str(9223372036854775808)` | `None` |
| 桁数が多すぎる | `"9" * 30`・`"1" * 5000` | `None`（`int()`の桁数の上限を超える文字列でも例外にならない） |
| 数字以外 | 空文字・空白・`"abc"`・`"-1"`・`"+1"`・`"1.5"`・`"1e3"`・前後に空白のある数字 | `None` |
| ASCII以外の数字 | `"²"`・`"１２"`（全角） | `None`（`isdigit()`は`"²"`もTrueになり`int()`で変換できないため） |

---

### 14. `management/commands` — 管理コマンド

**テストファイル**: `tests/test_management_commands.py`

#### 14-1. `delete` コマンド

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 通常削除 | `delete <id>` | SongがDBから削除される（`Song.all_objects`でも取得できない） |
| ユーザーが削除した曲（#1239） | `is_removed=True`の曲に`delete <id>` | SongがDBから削除され、紐づく`SongLink.is_removed`が`True`になる |
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
| 模倣された作者数が月ごとの累積値で保存される（#1163） | 1月の曲・2月の曲（作者あり）と、その両方を模倣する2月の模倣曲が存在、1月分の`Stats`に`total_imitated_authors=99`が入った状態で実行 | 1月分は1、2月分は2に再計算して上書きされる |
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
| ユーザーが削除した曲は除外（#1239） | `is_removed=True`の曲が存在 | ページが404になるため、その曲の`/songs/<id>/`・`/songs/<id>/history/`は含まれない |
| 作者 | Authorが存在 | `/authors/<id>/`・`/authors/<id>/stats/`・`/authors/<id>/aliases/`が含まれ、存在しない旧パス`/author/<id>/`は含まれない |
| 旧形式のchannel | Authorが存在 | リダイレクト用の`/channel/<name>/`は含まれない |
| 記事 | 公開・非公開・news記事が混在 | 公開かつnews以外の記事のみ`/articles/<id>/`が含まれる |

#### 14-8. `timeline` コマンド（すべあな界隈年表の読み取りと曲の登録・更新、#52）

すべあな界隈年表（Googleスプレッドシート）の2018年〜今年のシートを読み取り、年ごとの件数を出力したあと、`import_timeline`（27-2）で曲を登録・更新して結果を出力する。`get_timeline`（26-2）はモック化する。今年はサーバーOSのタイムゾーン（本番はUTC）によらず、`timezone.localtime(timezone.now())`で日本時間の年にする。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 日本時間の今年まで | `--year`未指定・`timezone.now()`がUTCの2026年12月31日15時（日本時間の2027年1月1日） | `get_timeline`に2018〜2027年が渡される |
| `--year`指定 | `--year 2020 2021` | `get_timeline`に2020・2021年のみが渡される |
| 新規作成と結果の出力 | 2018年に1件・2019年に2件（URLは登録されていない） | 標準出力に「2018年：1件」「2019年：2件」、曲ごとの「〇〇を新規作成（`<ROOT_URL>/songs/<id>`）」、「新規作成：3件、更新：0件、変更なし：0件、対象外のカテゴリ：0件、スキップ：0件」が出る。標準エラー出力は空で、Discordには通知しない |
| 更新の出力 | 行のURLが登録されている曲のカテゴリが異なる | 「曲のカテゴリを編集（`<ROOT_URL>/songs/<id>`）」と「更新：1件」が出る |
| スキップの出力 | URLの無い行が2件・カテゴリが「解読」の行が1件 | 「対象外のカテゴリ：1件、スキップ：2件」と理由ごとの件数「登録できるURLが無い：2件」が出る。行ごとの「スキップ：2018年2行目 曲1（登録できるURLが無い）」は`-v 2`のときのみ出る |
| 想定していないカテゴリ | カテゴリが「新カテゴリ」の行が2件 | 標準エラー出力に「カテゴリ「新カテゴリ」の2行は、登録・更新するかが決まっていないためスキップしました」が出て、曲は作らない |
| `--dry-run`指定 | 新規作成する行が1件 | 「〇〇を新規作成」と「（dry-run）新規作成：1件」が出るが、Song・SongLink・History・Editor・SongTimeline（#1269）は保存されない。ロールバックできないDiscordへの通知もしない |
| シートが無い年 | `--year 2018 2019`・`get_timeline`が2018年のみを返す | 標準エラー出力に「2019年のシートがありません」が出る。2018年の行は登録する。年が変わった直後などで起こりうるため、Discordには通知しない |
| `--json`指定 | 2018年に日付ありの1件・2019年に日付なしの1件 | 標準出力が行のJSONの配列になる（`date`は`YYYY-MM-DD`か`null`）。曲は登録しない |
| 読み取りに失敗 | `get_timeline`が`TimelineError`を送出 | PythonAnywhereのtasksで失敗を検知できるよう、`CommandError`を送出する（0以外の終了コードで終わる）。Discord（`ERROR_DISCORD_URL`）にエラーを通知し、曲は登録しない |
| 取り込み中の想定外のエラー | `import_timeline`が`RuntimeError("DBの詳細")`を送出 | 例外をそのまま送出する（トレースバックはtasksのログに残る）。`ERROR_DISCORD_URL`は公開チャンネルのため、Discordには例外のクラス名（`RuntimeError`）のみを通知し、「DBの詳細」は含めない |

#### 14-9. `deploy` コマンド（リロードの再試行と、失敗を終了コードで伝える処理、#1300）

`git pull`・`pip install`・`migrate`・`collectstatic`・`appversion` を順に実行したあと、PythonAnywhereのAPIでアプリをリロードする。2026-10-31のデプロイで、リロードのPOSTが一時的な`Connection refused`で失敗したのに、1回しか試さず終了コード0で終わっていたため、一時的な失敗は再試行し、最後まで失敗したら`CommandError`で0以外の終了コードで終える（`timeline`コマンドと同じ方針）。`subprocess.check_output`・`requests.post`・`time.sleep`はモック化し、`PYTHONANYWHERE_USERNAME`・`PYTHONANYWHERE_TOKEN`・`VENV_PATH`は実行環境の`local_settings`に依存しないよう差し替える。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| リロードが成功 | `requests.post`が200を返す | `git pull origin main`・`pip install -r requirements.txt`・`migrate`・`collectstatic --noinput --clear`・`appversion`の順に実行し、`timeout`を付けたPOSTを1回だけ送る。待機はせず、標準出力に「デプロイが完了しました。」が出て、標準エラー出力は空 |
| `-m` / `--no-migrate` | どちらかを指定 | `migrate`だけが実行されず、残りの手順とリロードは通常どおり行われる |
| `VENV_PATH`の指定 | `VENV_PATH="/venv"` | `pip`・`python`が`/venv/bin/pip`・`/venv/bin/python`になる（`git pull`は変わらない） |
| 接続エラーの後に成功 | POSTが`ConnectionError`を2回送出した後、200を返す | 3回目で成功して正常終了し、`RELOAD_RETRY_INTERVAL`秒の待機を2回行う。標準エラー出力に失敗の理由（`Connection refused`）と再試行する旨が出る |
| タイムアウトの後に成功 | POSTが`Timeout`を送出した後、200を返す | 2回目で成功して正常終了する |
| 5xxの後に成功 | POSTが503を返した後、200を返す | 2回目で成功して正常終了する。標準エラー出力にステータスコード（503）が出る |
| 上限まで失敗 | POSTが`RELOAD_MAX_ATTEMPTS`回続けて`ConnectionError`・`Timeout`・502のいずれかになる | `CommandError`（「リロードに失敗しました」）を送出する。POSTは`RELOAD_MAX_ATTEMPTS`回で、待機はその1回少ない回数（最後の試行の後は待たない） |
| 失敗時のメッセージ | 上限まで失敗（通常と`-m`の2通り） | 失敗の理由、「アプリは再起動されていません」、完了した手順の一覧、復旧方法（PythonAnywhereのWebタブのReload、または`python manage.py deploy -m`の再実行）を含む。`-m`のときは実行していない`migrate`を完了した手順に含めない |
| 4xx | POSTが401・404を返す | 再試行せず（POSTは1回、待機なし）、ステータスコードとレスポンスの内容を含む`CommandError`を送出する |
| レスポンスの内容が長い | 502のレスポンスが1000文字（HTMLのエラーページを想定） | `CommandError`のメッセージには、先頭`RELOAD_ERROR_BODY_MAX_LENGTH`（200）文字と「…」だけを含める。ちょうど200文字のときは切り詰めず「…」を付けない |
| 再試行中の警告でもレスポンスの内容を切り詰める | 503の長いレスポンスの後に200 | 標準エラー出力の警告にステータスコード（503）は出るが、レスポンスの内容は200文字を超えない |
| 再試行できない通信の例外 | POSTが`InvalidURL`を送出 | 再試行せず（POSTは1回、待機なし）、`CommandError`を送出する |
| コマンドの失敗 | 2つ目の`check_output`が`CalledProcessError`（終了コード2）を送出 | 失敗したコマンドと終了コードを含む`CommandError`を送出し、後続のコマンドとリロードは実行しない |
| 設定が空 | `PYTHONANYWHERE_USERNAME`または`PYTHONANYWHERE_TOKEN`が空文字列 | `CommandError`を送出し、コマンドの実行もリロードも行わない |

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

#### 15-2. `get_url(song)`（#1218、#1229）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| URL未登録 | フラグなし・`song.links` が空 | 「URL未登録」と曲の編集ページへのリンクを表示し、フラグのアイコンは出ない |
| URLあり | `song.links` にYouTubeのURL | URLへのリンクとYouTubeのアイコンを表示し、「URL未登録」は出ない |
| 各フラグのアイコン | `is_questionable`・`is_draft`・`is_original`・`is_joke`・`is_inst`（歌詞あり）・`is_deleted`・`is_special`・`is_limited` のいずれかが `True`、または `is_subeana=False` | 曲ページのタグと同じクラス・`title` の `<i>` タグが出て、ほかのフラグのアイコンは出ない |
| フラグなし | すべてのフラグが既定値・URLあり | フラグのアイコンは出ない |
| 界隈曲?の非すべあな曲 | `is_questionable=True`・`is_subeana=False` | 界隈曲?のアイコンだけが出て、非すべあな模倣曲のアイコンは出ない |
| アイコンの順番 | `is_draft=True`・`is_limited=True`・URLあり | 曲ページのタグと同じ順で並び、フラグのアイコンはURLのアイコンより前に出る |
| 非公開でURL未登録 | `is_deleted=True`・`song.links` が空 | 非公開のアイコンを表示し、「URL未登録」は出ない |
| フラグありでURL未登録 | `is_draft=True`・`song.links` が空 | 下書きのアイコンの後に「URL未登録」を表示する |
| フラグとURLの間の縦線 | `is_draft=True`・URLあり | フラグのアイコンとURLのアイコンの間に縦線（`song-card-separator`）が1つ入る |
| 非公開とURLの間の縦線 | `is_deleted=True`・URLあり | 非公開のアイコンとURLのアイコンの間に縦線が1つ入り、「URL未登録」は出ない |
| 複数URLの縦線 | `is_draft=True`・URLが2件 | 縦線は1つだけで、どちらのURLのリンクよりも前に入る |
| フラグとURL未登録の間の縦線 | `is_draft=True`・`song.links` が空 | 「URL未登録」の前に縦線が入る |
| フラグなしは縦線なし | フラグなし・URLあり | 縦線は入らない |
| リンクなしは縦線なし | `is_deleted=True`・`song.links` が空 | 非公開のアイコンだけで、縦線は入らない |
| 歌詞の欄に「インスト曲」と出る曲 | `is_inst=True`・`is_deleted=True`・歌詞が空 | インスト曲のアイコンに `song-card-sp-only`（PC幅では隠す）が付き、非公開のアイコンには付かない |
| 界隈曲?のインスト曲 | `is_inst=True`・`is_questionable=True`・歌詞が空 | 歌詞の欄が出ないため、インスト曲のアイコンに `song-card-sp-only` は付かない |
| インスト曲だけのときの縦線 | `is_inst=True`・歌詞が空・URLあり | 縦線にも `song-card-sp-only` が付く |
| インスト曲とほかのフラグがあるときの縦線 | `is_joke=True`・`is_inst=True`・歌詞が空・URLあり | 縦線には `song-card-sp-only` が付かない |
| フラグが2個 | `is_draft=True`・`is_limited=True`・URLあり | どちらのアイコンにもクラスは付かず、三点リーダー（`fa-ellipsis-h`）のアイコンは出ない |
| フラグが3個 | `is_draft=True`・`is_joke=True`・`is_limited=True`・URLあり | 下書きのアイコンはそのまま、ネタ曲・限定公開のアイコンに `song-card-pc-only`（スマホ幅では隠す）が付く。その後に `title` がネタ曲・限定公開の三点リーダーのアイコン（`song-card-sp-only`）が出て、縦線の前に入る |
| フラグが4個 | `is_original=True`・`is_joke=True`・`is_deleted=True`・`is_subeana=False`・URLあり | オリジナル模倣のアイコンの後に、`title` がネタ曲・非すべあな模倣曲・非公開/削除済みの三点リーダーのアイコンが出る |
| まとめられる、歌詞の欄に「インスト曲」と出る曲 | `is_original=True`・`is_inst=True`・`is_deleted=True`・歌詞が空・URLあり | PC幅でもスマホ幅でも出ないインスト曲のアイコンは出力しない。三点リーダーの `title` にはインスト曲を含め、縦線にはクラスが付かない |
| まとめられる、リンクなし | `is_original=True`・`is_joke=True`・`is_deleted=True`・`song.links` が空 | 三点リーダーのアイコンが出て、縦線と「URL未登録」は出ない |

#### 15-3. `get_lyrics(song)`（#1253）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 歌詞あり | `lyrics="テスト歌詞"` | 歌詞のアイコンと歌詞を表示 |
| 歌詞の特殊文字 | `lyrics="<script>"` | HTMLエスケープされる |
| 歌詞なしのインスト曲 | `is_inst=True`・歌詞が空 | 「インスト曲」を表示 |
| 歌詞なしの曲 | カテゴリが曲・歌詞が空 | 「歌詞未登録」と曲の編集ページへのリンクを表示 |
| 歌詞なしの曲以外 | カテゴリが曲以外（アレンジ・音MAD・メドレー・総集編・予告・オフボ・カバー・ネタ動画のそれぞれ）・歌詞が空 | 歌詞の登録が不要なため、何も表示しない |
| 歌詞なしの界隈曲? | `is_questionable=True`・カテゴリが曲・歌詞が空 | 歌詞の登録が不要なため、何も表示しない |
| 歌詞ありの曲以外 | `category="cover"`・`lyrics="テスト歌詞"` | 歌詞のアイコンと歌詞を表示 |
| 歌詞なしのインストの曲以外 | `category="arrange"`・`is_inst=True`・歌詞が空 | 「インスト曲」を表示 |
| 未完成の判定と一致 | 全カテゴリと `is_questionable=False`・`True` のそれぞれで、`is_original=True`・URLあり・歌詞が空 | 「歌詞未登録」と表示するのは `Song.is_lack()` が `True` の曲（界隈曲?ではなく、カテゴリが曲）だけ |

#### 15-4. `is_subeana_author(song)` と曲カードの背景色（#1219）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 全てあなたの所為です。の曲 | `song.authors` が作者ID 1（`SUBEANA_AUTHOR_ID`）のみ | `True` |
| 全てあなたの所為です。との合作 | `song.authors` がほかの作者と作者ID 1 | `True` |
| ほかの作者の曲 | `song.authors` が作者ID 1 以外のみ | `False` |
| 作者0人 | `song.authors` が空 | `False` |
| prefetch済みの作者 | `prefetch_related("authors")` で取得した作者ID 1 の曲 | クエリを発行せずに `True` を返す |
| 曲カードのクラス | 作者ID 1 の曲とほかの作者の曲を `render_song_card` で描画 | 作者ID 1 の曲のカードだけ、半透明の青色の背景にする `song-card-subeana-author` のクラスが付く |

---

### 16. `lib/author_alias_service.py` — 別名Discord通知・名義の統一サービス（#992、#1137、#1230）

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
| `source_authors`の順（#1230） | 別名の登録順と、Authorのid順・名前順が逆になるようにする | 別名の登録順（別名一覧画面の統一するフォームの候補の順）に並ぶ |
| `song_author_pairs()`・`affected_source_authors()` | past別名と同名のAuthorのうち、一方だけがSongを持つ | `song_author_pairs()`は`(song_id, author_id)`の一覧を返し、`affected_source_authors()`は曲を持つAuthorのみを返す |
| 統一先が既存Authorの場合の`affected_source_authors()` | 統一先が既存Authorで、authorがSongを持たない | 別名・リンクを移すため、曲が無くてもauthor自身が含まれる |

#### 16-4-2. `get_ununified_source_authors(author)`（#1230）

以前の名称と同名で、まだ曲が残っている別のAuthorと、その曲数を`(Authorのリスト, 曲数)`で返す。現在の名義のまま統一した場合に曲を移すAuthorで、`build_unify_name_plan(author, author.name)`から算出するため、`AuthorUnifyNameSetView`で`unify_noop`になる条件と一致する。別名一覧画面の「名義を統一する」の状態の表示に使う。

別名一覧画面を開くたびに呼ばれるため、統一元の曲を全件取得する`song_author_pairs()`は使わず、曲を持つAuthorのid（`DISTINCT author_id`）と曲数（`COUNT(DISTINCT song_id)`）だけを集計する。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| past別名と同名のAuthorが無い | past別名のみ登録 | `([], 0)`（統一済み） |
| past別名と同名のAuthorが曲を持たない | 統一済みで曲数0のAuthorが残っている状態（#1137） | `([], 0)`（統一済み） |
| past別名と同名のAuthorが曲を持つ | 2曲を持つAuthorと、曲を持たないAuthor | `([曲を持つAuthor], 2)`。曲を持たないAuthorは含まない |
| 共著の曲は1曲として数える | 1曲が2つのpast別名のAuthorの共著 | 両方のAuthorを含み、曲数は1 |
| author自身の曲は数えない | authorのみがSongを持つ | `([], 0)` |
| past以外の別名と同名のAuthorは対象外 | `another`別名と同名のAuthorがSongを持つ | `([], 0)` |
| 曲を1曲ずつ取得しない | past別名と同名のAuthorが5曲を持つ | `([そのAuthor], 5)`。曲と作者の中間テーブルへのクエリは2件で、どちらも`DISTINCT`による集計（曲を1行ずつ取得するクエリを発行しない） |
| 統一済みなら曲数を集計しない | past別名と同名のAuthorが曲を持たない | `([], 0)`。`COUNT`のクエリを発行しない |

#### 16-4-3. `find_unify_name_conflict_authors(plan)`（#1290）

旧名を統一先の新たな`past`別名として登録し直せない原因になるAuthorを、id順に返す。`AuthorAlias.name`はグローバルにuniqueなため、author・統一先以外のAuthorが旧名と同名の別名を持っていると登録できない。`AuthorUnifyNameSetView`・`AuthorUnifyNameConfirmView`が、原因の作者を別名一覧画面で伝えるために使う。

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 衝突なし | 旧名と同名の別名を誰も持たない | `[]` |
| 別authorが旧名と同名の別名を持つ | 別authorが`another`別名で旧名を保有 | `[その別author]` |
| 統一先が既存Author | 同上で、選択したpast別名と同名のAuthorが統一先になる | `[その別author]` |
| author自身が保有 | author自身が旧名と同名の別名を持つ | `[]` |
| 統一先が保有 | 統一先のAuthorが旧名と同名の別名を持つ | `[]`（統一後はそのまま再利用するため衝突ではない） |
| 現在の名前を選択 | `new_name=author.name`で、別authorが旧名と同名の別名を持つ | `[]`（旧名の再登録が起きないため） |
| 複数のAuthor | `group`別名を2つのauthorが保有し、うち1人は`spell`別名でも同名を持つ | 各authorを1回ずつ、id順に返す |

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

`compute_view_like_totals`はsong_count/total_view/total_likeのみを返す最小構成（total_imitateds/total_authorsを含まない）。`get_view_like_pairs`はqs内の各曲のview/likeを`(view, like)`のペアのリストとして列挙する（Noneは0扱い）。鍵歴（#968、`kenreki_service.py`参照）はSongごとに算出してから合計する仕様のため、集計済みのSumではなくこちらを使う。`compute_base_stats`は`compute_view_like_totals`に`total_imitateds`を加えたもの、`compute_common_stats`はさらに`total_authors`（`compute_unique_author_count`によるAuthor起点の追加クエリ）と`total_imitated_authors`（`compute_imitated_author_count`、#1163）を加えたもので、総合統計ページ・stats管理コマンドのみが使う。authorごとの統計ページはtotal_authorsを画面に表示しない（合作人数を別途算出するため）ため`compute_base_stats`を使い、無駄なクエリが発行されないようにしている（コードレビュー指摘対応）。

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
| ユーザーが削除した模倣曲（#1239） | `compute_base_stats` | 通常の曲と削除した曲がある曲を模倣 | `total_imitateds`は1（削除した曲は数えない） |
| ユーザーが削除した曲（#1239） | `compute_base_stats` | 通常の曲(view=100)と削除した曲(view=50)、`Song.objects.all()`を渡す | `song_count`は1、`total_view`は100 |
| 同じ作者が複数曲に関わる | `compute_common_stats` | 作者Aが2曲、作者Bが1曲（Aと共作） | `total_authors`は重複を除いた人数（2）になる（`compute_unique_author_count`を内部で使用、#334で`song.authors`の総和から変更） |
| 模倣された作者数を含む（#1163） | `compute_common_stats` | 作者の曲が1曲に模倣されている | `total_imitated_authors`が1になる |
| 空のqueryset（#1163） | `compute_common_stats` | 曲が0件 | `total_imitated_authors`が0 |
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
| ユーザーが削除した原曲を模倣（#1239） | 1曲が通常の曲と削除した曲を模倣 | `compute_total_imitates`が1（削除した曲は数えない） |

#### 19-3-0. `compute_imitated_author_count(qs)`（#1163）

「1度でも模倣されたことのある作者数」の算出に使用（総合統計ページ・stats管理コマンドの`total_imitated_authors`）。qs内の曲のうち、削除されていない曲に1度でも模倣された曲の作者を、重複なしで数える。模倣曲の投稿日時はqsの絞り込みに関わらず見ない（`total_imitateds`と同じ扱い）。

| テストケース | 前提条件 | 期待結果 |
| --- | --- | --- |
| 空のqueryset | 曲が0件 | 0 |
| 模倣された曲の作者 | 作者Aの曲が別の曲に模倣されている | 1 |
| 模倣していない作者は数えない | 原曲の作者と、原曲を模倣した曲の作者が存在 | 原曲の作者のみの1（模倣した側の作者は、自分の曲が模倣されていなければ数えない） |
| 複数の曲が模倣されていても1人 | 作者Aの2曲がそれぞれ模倣されている | 1 |
| 共作曲 | 作者A・Bの共作曲が模倣されている | 2（共作者全員を数える） |
| 削除した模倣曲のみに模倣された作者（#1239） | 原曲を、削除した曲だけが模倣している | 0 |
| 通常の模倣曲と削除した模倣曲の両方 | 原曲を、削除した曲と通常の曲が模倣している | 1 |
| qs外の曲 | qsに含まれない曲の作者の曲も模倣されている | qs内の曲の作者のみが数えられる |
| 作者数・模倣曲数の相互干渉防止（回帰） | 複数作者かつ3つの模倣曲を持つ曲 | 作者数の2のまま水増しされない |

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
| 2件目以降の差分 | 2件の行リスト | 直前の行との差分になる（`total_imitated_authors_delta`を含む、#1163） |
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

### 24. `lib/ip.py` — クライアントのIP（#1188、#1189）

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

#### 24-2. `get_ip(request, raw=False)`（#1189）

編集者（`Editor`）の識別・お問い合わせのIP・BANされた編集者（`Editor.is_banned`）の判定に使うIP。`get_client_ip`と同じIPを使い、`raw=False`の場合は`encrypt`した値を返す。以前は`X-Forwarded-For`の先頭を使っており、他人のIPを名乗ってその人の編集者として編集できた。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| X-Real-IPを使う | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP: 203.0.113.1` | `raw=True`で`203.0.113.1`、`raw=False`で`encrypt("203.0.113.1")` |
| X-Forwarded-Forは使わない | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP: 203.0.113.1`、`X-Forwarded-For: 198.51.100.1, 203.0.113.1` | `raw=True`で`203.0.113.1`、`raw=False`で`encrypt("203.0.113.1")` |
| X-Real-IPが無い | `REMOTE_ADDR: 10.0.0.1`、`X-Forwarded-For: 198.51.100.1` | `raw=True`で`10.0.0.1`、`raw=False`で`encrypt("10.0.0.1")` |
| X-Real-IPがIPでない | `REMOTE_ADDR: 10.0.0.1`、`X-Real-IP: not-an-ip` | `encrypt("10.0.0.1")`（IPでない値は`encrypt`で扱えないため） |

---

### 25. `templatetags/changes.py` — 変更履歴の表（#608）

**テストファイル**: `tests/test_templatetags_changes.py`

#### 25-1. `render_changes(history)`

編集の変更履歴の表には`diff-table`クラスを付け、`editor.js`が編集前と編集後のセルに差分（削除は`<del>`、追加は`<ins>`）を表示する。保存するデータ（`History.changes`）は変えない。2026/4/11以前は編集も`history_type="new"`で保存されていたため、`history_type`ではなく`changes`の見出し（`EDIT_CHANGES_HEADER`）で判定する。差分の求め方と表示はDjangoテストでは確認できないため、Playwrightで確認する（結合テスト計画書の21-2）。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 編集 | `history_type="edit"`、`changes`の見出しが`["種類", "編集前", "編集後"]` | `<table class="diff-table">`になり、編集前・編集後のセルが出力される |
| 以前の形式の編集 | `history_type="new"`、`changes`の見出しが`["種類", "編集前", "編集後"]` | `<table class="diff-table">`になる |
| 新規作成 | `history_type="new"`、`changes`の見出しが`["種類", "内容"]` | `<table>`のままで、`diff-table`は含まれない |
| 削除 | `history_type="delete"`、`changes=["理由", "削除理由"]` | `<table class="delete-table">`のままで、`diff-table`は含まれない |
| changesが無い | `changes=None` | 表を出力しない |
| セルの改行とエスケープ | 編集前`"<b>1行目\n2行目"`、編集後`"1行目\r\n2行目"` | `<td>&lt;b&gt;1行目<br>2行目</td>`・`<td>1行目<br>2行目</td>`（JSはセルのテキストと`<br>`から元の文字列を取り出す） |

---

### 26. `lib/timeline.py` — すべあな界隈年表の読み取り（#52）

**テストファイル**: `tests/test_lib_timeline.py`

すべあな界隈年表（Googleスプレッドシート）の年ごとのシートを、Google Sheets APIで読み取る。Issueの指定どおり読み取り専用とするため、OAuthの認証情報ではなくAPIキー（公開されているスプレッドシートの読み取りしかできない）を使い、`spreadsheets.get`と`spreadsheets.values.batchGet`のみを呼び出す。Google Sheets API（`build`）はモック化する。元の例外の文字列にはAPIキーを含むURLが入るため、YouTube Data API連携（21）と同様に例外は連鎖させず（`from None`）、メッセージにはHTTPステータス・理由・元の例外のクラス名のみを入れる。

#### 26-1. `parse_sheet(year, values, merges=(), sheet_id=None)`

各年のシートは同じ見出し（`EXPECTED_HEADER`）で、見出しが空の列は直前の列の続き（2つ目以降の解読URL・配信URL）として使われている。日付は空なら直前の行と同じ日。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 列ごとの値 | 全ての列に値がある行 | 各フィールドに対応する列の値が入る。`urls`はURL・URL2、`decode_urls`は解読URLと右の見出しの無い2列、`distribution_urls`は配信URLと右の見出しの無い2列、`notes`は備考と、それより右の見出しの無い列 |
| 行末のセルが無い | `["5/10", "", "曲名"]`（APIは行末の空のセルを返さない） | 無い列の値は`""`、リストは`[]` |
| 空のセルはリストに入れない | URL2・3つ目の解読URLのみ値がある | `urls`・`decode_urls`に空文字列が入らない |
| 前後の空白 | `" 5/10 "`・`" 曲名\n"`・`" 🍁🍜\n🐬+ "` | 前後の空白を取り除く。セル内の改行は残す |
| 空白文字のみのタイトル・作者 | タイトルが全角スペースのみ・作者が半角スペースのみ・バッジが全角スペースのみ | 全角スペースのみのタイトルなどもあるため、タイトル・作者は取り除かずにそのまま残す。それ以外の列は`""` |
| 日付の引き継ぎ | 日付が空・全角スペースのみの行 | 直前の行の日付になる |
| 最初の日付より前の行 | 1行目の日付が空 | `date=None` |
| 日付として読めない値 | `不明`・`2/30`・`2024/1/1` | `date=None`。次の日付が空の行も`None`を引き継ぐ |
| うるう日 | 2024年・2025年の`2/29` | 2024年は2024年2月29日、2025年は`None` |
| 空の行 | 空のリスト・空白のみの行 | 読み飛ばす。`row`はシートの行番号のまま（見出しが1行目） |
| 見出しのみ | 見出しの行のみ | `[]` |
| 備考より右に列が増えた | 見出しの末尾に列を追加 | 既存の列の並びは変わらないため読み取る |
| 見出しが異なる | 列の入れ替え・備考が無い・列が少ない | 別の列の値を読み取らないよう、`TimelineError`（「〇〇年のシートの見出しが想定と異なります」）を送出する |
| 空のシート | `values=[]` | `TimelineError`を送出する |
| プ列のセル結合（#1064） | プ列の2〜3行目を結合し、一番上の行だけに「年末プレラ５」がある。3〜4行目にプ列以外の列の結合もある | 2〜3行目の`premiere_rush`は「年末プレラ５」、4〜5行目は`""`（APIは結合したセルの値を一番上の行にしか返さないため、結合した範囲の行に入れる。プ列以外の結合は使わない） |
| プ列の結合が無い行（#1064） | `" 夏プレラ "`・空欄 | `"夏プレラ"`・`""` |
| シートのID（#1269） | `sheet_id=123` | 全ての行の`sheet_id`が123（曲のページの「年表で見る」ボタンのURLに使う） |

#### 26-1-1. `fill_premiere_rush_continuations(rows)`（#1064）

プ列は、結合した範囲の後の行に「︙」「⋮」「...」を書いて、直前の行のプレラの続きを表している。

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| 続きの記号 | 「年末プレラ５」・「︙」・「⋮」・「...」・空欄・「︙」・「夏プレラ」・「︙」 | 「年末プレラ５」×4・空欄×2・「夏プレラ」×2（空欄の後の記号は空欄のまま） |
| 先頭の行が続きの記号 | 「︙」・空欄 | 空欄・空欄 |

#### 26-2. `get_timeline(years)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 年ごとの行 | 2018年・2019年のシートがある | `{2018: [...], 2019: [...]}`を返す。`spreadsheets.get`は`fields="sheets(properties(title,sheetId),merges)"`（シートの名前・ID（#1269）とセル結合の範囲）、`batchGet`は`ranges=["'2018年'", "'2019年'"]`で呼ばれる |
| APIキーのみを使う | 正常実行 | `build("sheets", "v4", developerKey=<APIキー>, cache_discovery=False)`で呼ばれる |
| 書き込みのAPIを呼ばない | 正常実行 | `spreadsheets.batchUpdate`・`create`、`values.update`・`append`・`clear`・`batchUpdate`・`batchClear`が呼ばれない |
| シートが無い年 | 2018〜2020年のうち2019年のシートが無い | 2019年は返さず、`batchGet`にも含めない |
| 対象のシートが1つも無い | 年のシートが無い | `{}`を返し、`batchGet`を呼ばない |
| 空のシート | `valueRanges`に`values`が無い | `TimelineError`（見出しが想定と異なります）を送出する |
| `valueRanges`の数が違う | 2年分を要求して1件のみ返る | `TimelineError`（レスポンスを解析できませんでした）を送出する |
| APIの呼び出しに失敗 | `batchGet`が`HttpError` 400・403・404・500を送出 | `TimelineError`を送出し、メッセージにHTTPステータスと理由が含まれ、APIキーは含まれない。例外が連鎖していない（`__cause__`が`None`・`__suppress_context__`が`True`） |
| シート一覧の取得に失敗 | `spreadsheets.get`が`HttpError` 404を送出 | `TimelineError`を送出し、`batchGet`を呼ばない |
| 通信エラー・タイムアウト | `socket.timeout` | `TimelineError`を送出し、メッセージに元の例外のクラス名が含まれる。例外が連鎖していない |
| 設定が無い | `GOOGLE_SHEETS_API_KEY`または`GOOGLE_SHEETS_SPREADSHEET_ID`が空・`local_settings.py`に定義自体が無い | 設定は`getattr(settings, ...)`で読むため、importで止まらずに`TimelineError`（設定されていません）を送出し、APIは呼び出さない |
| 年をまたぐプレラ（#1064） | 2023年のシートの最後の行が「年末プレラ４」（結合）、2024年のシートの先頭の行が「︙」 | 2024年の先頭の行も「年末プレラ４」になる（年末のプレラは翌年のシートの先頭まで続くため） |
| シートのID（#1269） | 2018年のシートの`sheetId`が123、2019年のシートに`sheetId`が無い | 2018年の行の`sheet_id`は123、2019年の行は0（APIは値が0の項目をレスポンスから省くため） |

#### 26-3. `get_timeline_url(sheet_id, row, column=None)`（#1269）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 行を選択するURL | `GOOGLE_SHEETS_SPREADSHEET_ID="sheet-id"`・`sheet_id=123`・`row=45` | `https://docs.google.com/spreadsheets/d/sheet-id/edit#gid=123&range=45:45`（実際の年表で、45行目を選択した状態で開くことを確認した） |
| 列のセルを選択するURL | `column=14`・`column=0` | `#gid=123&range=O45`・`#gid=123&range=A45`（「年表に登録する」ボタンは歌詞列（O列、`LYRICS_COLUMN`）のセルを選択する） |
| スプレッドシートのIDが無い | `GOOGLE_SHEETS_SPREADSHEET_ID=""` | `None` |

---

### 27. `lib/timeline_import.py` — すべあな界隈年表からの曲の登録・更新（#52）

**テストファイル**: `tests/test_lib_timeline_import.py`

年表の行のうち、カテゴリが`CATEGORY_MAP`にある行を曲として登録・更新する（「曲」「DSC」「逆再生枠」・空欄→曲（空欄は新規作成のときのみ。更新ではカテゴリを変えない）、「アレンジ」→アレンジ、「音mad」→音MAD、「メドレー」→メドレー、「総集編」→総集編、「予告」→予告、「オフボ」→オフボ、「カバー」→カバー、「ネタ」→ネタ動画）。「解読」「その他」「配信」「企画」「出来事」「不明」は対象外で、どちらにも無いカテゴリは年表に新しく追加されたものとしてコマンドが警告する。

- **照合**: 行のURL（URL列・URL2列を`clean_url`で短縮・フォーマットし、`get_allow_media`で許可されているもののみ。`youtube.com/live/<id>`も`clean_url`で短縮URLになる。「https://」の無い`youtu.be/<id>`には「https://」を付ける）が登録されている曲を更新する。DBには「www.」付き・http・大文字小文字の違うURLもあるため、比較用に揃えてから照合する（XのユーザーIDなどは大文字小文字を区別しないため小文字にそろえるが、YouTube・ビリビリ動画の動画IDは区別する。ビリビリ動画のURLは`clean_url`でBV番号のURLに揃うため、av番号のURLも同じ動画として扱う（#1246）。ニコニコ動画はスマホ版（`sp.nicovideo.jp`）や「?ref=」などの違いも同じURLとして扱う）。複数の曲で共有しているURL（`allow_dup=True`）は、どの曲の行かを決める手がかりにしない。どのURLも登録されていなければ、歌詞列（`https://lyrics.imicomweb.com/songs/<id>`）の曲とタイトルか作者が一致すればその曲を更新し、一致しなければスキップする（作者だけが一致する場合は、full版の行の歌詞列がshort版の曲を指していることがあるため、short版かどうかも同じ曲に限る）（歌詞列が別の曲を指していることがあるため）。歌詞列の曲も無ければ新規作成する
- **新規作成**: タイトルは作品名/出来事列、作者は作者列（合作は改行で区切り、2人目以降の先頭に「+」が付くことがある。「+SSBA」のように「+」で始まる作者もいるため、1人目の「+」は削らない。作者名のカンマでは区切らない。0文字でなければ空白文字のみでも登録する）、カテゴリはカテゴリ列、模倣はモチーフ1列・モチーフ2列、URLはURL列・URL2列
- **更新**: URL・模倣は登録されていないものを追加し、カテゴリは年表の値にする。タイトル・作者は更新しない。ロックされた曲も更新する。`post_time`を更新し、編集画面と同様に変更した項目をHistoryの`changes`に残す
- **模倣**: モチーフ1列は末尾の「枠」、モチーフ2列は「→.[short]👤」形式なら先頭の矢印と末尾の絵文字1文字分（合作の曲は「→生合成🔢😥」のように作者のバッジが複数付くため、見つからなければバッジを全て）、「鵺🔢模倣」形式なら末尾の「模倣」とその前のバッジ（絵文字と「+」）を削除し、タイトルが完全一致する曲を模倣に追加する。「❁」「全てが適当すぎた.模倣」のように記号や「模倣」で終わるタイトルの曲もあるため、モチーフ2は削る前の文字列から順に探し、曲がある最初の候補にする。模倣元は多くがすべあなの曲で、同じタイトルのアレンジなども登録されているため、モチーフ1・モチーフ2とも、同じタイトルの曲が複数あればすべあな（Author id=1）の曲が1曲ならその曲にする（同じ実行で作ったすべあなの曲も含む）。すべあなの曲に決まらなければ追加しない。曲のタイトル・作者は最初に全て読み込み、行ごとにクエリは発行しない。年表での呼び方が曲のタイトルと異なるもの（「表裏」→「表/裏」、「名の無い星」→「名の無い星が空に堕ちたら」）は`MOTIF_TITLES`で変換する
- **プレラ（#1064）**: プ列のプレラを、新規作成では曲に付け、更新では登録されているプレラと違えば付け替える。プ列が空欄の行では、登録されているプレラを消さない。複数の行に一致する曲は、カテゴリと同様に最初の行のプレラにする。プレラの名前は、年末のプレラが翌年まで続くときなどに全角・半角が違うことがある（「年末プレラ３」と「年末プレラ3」）ため、NFKCで揃えて同じプレラにする。プレラはスキップすることが無くなってから作るため、スキップした行のプレラは残らない。プレラの日付（`Prush.date`）は、作るときはその行の日付にし、もっと古い日付の行があれば古い方にする。曲の検索の選択肢の並びに使うため、曲を登録・更新しない行（対象外のカテゴリ・スキップした行）の日付も使う。全角・半角だけが違うプレラが既に複数登録されている場合は、先に登録された（idの小さい）プレラを使う
- **TimelineSkip（#1064）**: 行ごとのトランザクションはロールバックされるが、メモリ上のキャッシュ（曲・URL・模倣・プレラなど）は戻らないため、DBやキャッシュを変える前にだけ送出する
- **年表の行（#1269）**: 曲（新規作成・更新・変更なし）が載っている行を`SongTimeline`に保存する。複数の行に一致する曲は、カテゴリ・プレラと同様に最初の行にする。スキップした行・対象外のカテゴリの行では保存しない。歌詞列が空か（`is_lyrics_blank`）も保存する。歌詞列で一致した行は歌詞列が空ではないため、歌詞列が空の行はURL列で一致した行（新規作成した曲の行を含む）に限られる。読み取った年の行に一致しなくなった曲の行は削除し、読み取っていない年（`--year`オプション）の行は残す
- **History**: 編集者はid=1のEditor（開発者）。削除されていればid=1で作り直す
- **毎日実行しても変わらないこと**: URLで照合できない行（登録できるURLが無い行）は毎日新規作成されてしまうため登録しない。複数の行に一致する曲は、カテゴリが行ごとに入れ替わらないよう最初の行（カテゴリが空欄の行を除く）のカテゴリにする。共有しているURLしか無い行も、次の実行でURLで照合できないため登録しない
- 行ごとにトランザクションで保存し、スキップした行（掲載拒否の作者など）で作った作者は残さない
- 取り込みではDiscordなど外部へ送信しない（`--dry-run`でDBの変更はロールバックされるが、外部への送信は取り消せないため）

#### 27-1. モチーフ・作者・URLの読み取り

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| モチーフ1 | `教育枠`・`.[short]枠`・`本家以外模倣` | `教育`・`.[short]`・`本家以外模倣` |
| モチーフ2（矢印の形式） | `→.[short]👤`・`→0⁰🔩`・`→春ノ海`・`→曲🍁🔩`・`→生合成🔢😥`・`→天秤にかけて🍁+`・`→曲^`・`→❁` | 先頭の矢印を除き、削る前・末尾の絵文字1文字分を削った後・作者のバッジ（絵文字と「+」）を全て削った後の順に候補にする（同じ候補は除く）：`[".[short]👤", ".[short]"]`・`["0⁰🔩", "0⁰"]`・`["春ノ海"]`・`["曲🍁🔩", "曲🍁", "曲"]`・`["生合成🔢😥", "生合成🔢", "生合成"]`・`["天秤にかけて🍁+", "天秤にかけて"]`・`["曲^"]`（絵文字でない記号は削らない）・`["❁"]`（削ると空になる候補は除く）。異体字セレクタ付きの絵文字・ZWJで繋がった絵文字も1文字分として削る |
| モチーフ2（模倣の形式） | `鵺🔢模倣`・`天秤にかけて🍁+模倣`・`蝕🍁🌌🌧️模倣`・`᠈[short]📺️模倣`・`全てが適当すぎた.模倣` | 末尾の「模倣」とその前のバッジ（絵文字と「+」）を削る前と後の順に候補にする：`["鵺🔢模倣", "鵺🔢", "鵺"]`。最後の候補は`天秤にかけて`・`蝕`・`᠈[short]`。`全てが適当すぎた.模倣`は`["全てが適当すぎた.模倣", "全てが適当すぎた."]` |
| モチーフ2（矢印・模倣の無い形式） | `名の無い星`・`K²🔩`・空文字列 | `["名の無い星"]`・`["K²🔩", "K²"]`・`[]` |
| 作者 | `作者A\n+作者B`・`作者A \n\n作者B`・`全て魚の所為で、`・`あんくらげ / Ankurage`・全角スペースのみ・空文字列 | 改行で区切り、2人目以降の先頭の「+」を削除する（`+SSBA`は`["+SSBA"]`のまま）。「、」「/」では区切らない。空白文字のみならそのまま1人の作者名にし、空文字列なら`[]` |
| URL | YouTube（`www.`・`m.`・`&t=`付き）・ニコニコ動画・Twitter・`youtube.com/live/<id>`・「https://」の無い`youtu.be/<id>`・`youtube.com/post/`・Discordのメッセージのリンク・途中で切れたURL（`.be/<id>`）・URLでない文字列・255文字を超えるURL | `https://youtu.be/<id>`・`https://nicovideo.jp/...`・`https://x.com/...`。ライブ・「https://」の無いURLは`https://youtu.be/<id>`にする（重複は除く）。許可されていないメディア・URLでないもの・長すぎるものは除く |

#### 27-2. `import_timeline(rows)`

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 新規作成 | URLが登録されていない行（カテゴリ「DSC」・作者2人・モチーフ1`教育枠`・モチーフ2`→K²🔩`） | タイトル・作者2人・カテゴリ`song`・短縮したURL・模倣（教育・K²）で曲を作り、編集者id=1・`history_type="new"`・「〇〇を新規作成」のHistoryを作る。`changes`にURL・カテゴリ・模倣が入る |
| カテゴリの対応 | `CATEGORY_MAP`の11種類と空欄 | それぞれ対応する`Song.category`で作る（空欄は曲） |
| 対象外のカテゴリ | 「解読」「その他」「配信」「企画」「出来事」「不明」 | 曲を作らず、`excluded`に数える |
| 想定していないカテゴリ | 「新カテゴリ」 | 曲を作らず、`unknown_categories`に入れる |
| 登録できるURLが無い | URLが無い・Discordのメッセージのリンク・`youtube.com/post/` | スキップ（URLで照合できず、毎日新規作成されてしまうため） |
| 新規作成できない行 | タイトルが0文字・501文字・作者が0文字・作者名が256文字・掲載拒否の作者を含む | それぞれの理由でスキップ。掲載拒否の作者の行で作った作者は残さない |
| 空白文字のみのタイトル・作者 | タイトルが全角スペースのみ・作者がタブのみ | 0文字ではないため、そのまま登録する |
| 削除された曲のURL | `is_removed=True`でどの曲にも紐づいていないSongLink | 新規作成しない（削除した曲を再び登録しない） |
| ユーザーが削除した曲のURL（#1239） | URLが`Song.is_removed=True`の曲だけに紐づく | 「削除された曲のURL」でスキップし、削除した曲を更新・作り直ししない（`self.songs`に無い曲を更新しようとして`KeyError`で止まらない） |
| ユーザーが削除した曲のURLを含む行（#1239） | 行のURLの一方が削除した曲に、もう一方が削除していない曲に紐づく | 「複数の曲に一致」でスキップせず、削除していない曲を更新する。削除した曲のURLは追加しない |
| 曲に紐づいていないSongLink | `is_removed=False`でどの曲にも紐づいていないSongLink | 新しく作らず、そのSongLinkを使う |
| 更新 | カテゴリ「曲」・模倣AAA・CCC・URL C・Bの曲に、カテゴリ「カバー」・モチーフAAA・BBB・URL A・Bの行 | タイトル・作者は変えず、カテゴリをカバー、URLをC・B・A、模倣をAAA・BBB・CCCにする。`post_time`を更新し、「曲のURLとカテゴリと模倣を編集」のHistory（編集者id=1・`history_type="edit"`・変更前後のURL・カテゴリ・模倣）を作る |
| 変更なし | 行と同じ内容の曲 | Historyを作らず、`unchanged`に数える |
| 2回目の実行 | 同じ行で2回実行 | 2回目は曲もHistoryも増えない |
| URLの表記の違い | DBに`http://www.nicovideo.jp/watch/SM1`・`https://x.com/SubeKashi/status/1`、行に`https://nicovideo.jp/watch/sm1`・`https://x.com/subekashi/status/1` | 同じURLとして照合し、URLを追加しない |
| ニコニコ動画のスマホ版・クエリ | DBに`https://nicovideo.jp/watch/sm1`、行に`https://sp.nicovideo.jp/watch/sm1?ref=user_video`・`https://nicovideo.jp/watch/sm1?ref=nicoiphone_other` | 同じURLとして照合し、URLを追加しない（重複した曲を作らない） |
| YouTubeの動画IDの大文字小文字 | DBに`https://youtu.be/aaaaaaaaaaa`、行に`https://youtu.be/AAAAAAAAAAA` | 動画IDは大文字小文字を区別するため、別の曲として新規作成する |
| ビリビリ動画のav番号・BV番号（#1246） | DBに`https://bilibili.com/video/BV1qV411J7Kq`、行に`https://www.bilibili.com/video/av417727107/`・`https://www.bilibili.com/video/BV1qV411J7Kq/?spm_id_from=...` | 同じ動画のURLとして照合し、URLを追加しない |
| ビリビリ動画のBV番号の大文字小文字 | DBに`https://bilibili.com/video/BV1qV411J7Kq`、行に`https://bilibili.com/video/BV1QV411J7KQ` | BV番号は大文字小文字を区別するため、別の曲として新規作成する |
| 外部への送信 | 更新する行・新規作成する行 | Discordへの送信（`requests.post`・`url.py`の`send_discord`）をしない |
| 複数の曲に一致 | 行のURLが別々の曲に登録されている | スキップし、どちらの曲も変えない |
| 共有しているURL（1曲に紐づく） | `allow_dup=True`のURLがメドレーの曲だけに紐づき、行はそのURLと未登録のURLを持つ | メドレーの曲を更新せず、新しい曲を作る。共有しているURLにも新しい曲を紐づける |
| 共有しているURL（複数の曲に紐づく） | `allow_dup=True`のURLが2曲に紐づき、行のもう一方のURLが曲に登録されている | 「複数の曲に一致」でスキップせず、もう一方のURLの曲を更新する |
| 共有しているURLのみ | 行のURLが`allow_dup=True`のURLだけ | 「複数の曲で共有しているURLのみ」でスキップし、曲を作らない |
| ロックされた曲 | `is_lock=True`の曲に一致 | ロックされていない曲と同様に、カテゴリを変えURLを追加する |
| 界隈曲?の曲 | `is_questionable=True`の曲に一致 | 編集画面と同様に模倣を追加しない |
| 削除された曲のURLを含む行 | 行のURLの一方が削除された曲のURL | そのURLは曲に追加しない |
| 同じタイトルの曲が複数（モチーフ2） | 「エヌ」の曲がすべあなと別の作者に1曲ずつ・モチーフ2が`→エヌ👤` | すべあなの「エヌ」を模倣に追加する |
| すべあなの曲が無いモチーフ2 | 「.」の曲が別の作者に2曲・モチーフ2が`→.👤` | 模倣に追加しない |
| 作者のバッジが複数のモチーフ2 | 「生合成」の曲があり、モチーフ2が`→生合成🔢😥`・`→生合成🔢+` | どちらの行も「生合成」を模倣に追加する |
| 同じタイトルの曲が複数（モチーフ1） | 「.」の曲がすべあなと別の作者に1曲ずつ・モチーフ1が`.枠` | すべあなの「.」を模倣に追加する |
| 同じ実行で作ったすべあなの曲（モチーフ1） | 別の作者の「原曲」がある状態で、1行目で作者が全てあなたの所為です。の「原曲」を作り、2行目のモチーフ1が`原曲枠` | 1行目で作った曲を模倣に追加する |
| すべあなの曲が無いモチーフ1 | モチーフ1`無題です。枠`（別の作者の曲が1曲）・`..枠`（別の作者の曲が2曲） | 1曲なら追加し、2曲なら追加しない |
| 呼び方の違う模倣元 | モチーフ1`表裏枠`・モチーフ2`名の無い星`（「表/裏」と別の作者の「表裏」がある） | 「表/裏」・「名の無い星が空に堕ちたら」を模倣に追加する |
| 記号や「模倣」で終わるタイトルの模倣元 | モチーフ2`→❁`（「❁」の曲がある）・`→曲★`（「曲★」と「曲」の曲がある）・`全てが適当すぎた.模倣`（その曲がある） | 削る前のタイトルの曲（「❁」・「曲★」・「全てが適当すぎた.模倣」）を模倣に追加する |
| 自身が模倣元 | モチーフ2が曲自身のタイトル | 模倣に追加しない |
| 同じrunで作った曲が模倣元 | 1行目で原曲を作り、2行目のモチーフ1が原曲 | 2行目の曲の模倣に1行目の曲を追加する |
| URLを共有する行 | 1行目（音mad）のURLを2行目（曲）がURL2列に持つ | 1行目で作った曲に2行目のURLを追加する。カテゴリは1行目の音MADのまま |
| カテゴリの異なる複数の行に一致 | アレンジの行・カバーの行が同じ曲に一致し、2回実行 | 最初の行のアレンジになり、Historyは1件のみ（毎回入れ替わらない） |
| 空欄のカテゴリの行で更新 | カテゴリがアレンジの曲に、カテゴリが空欄の行が一致 | カテゴリを変えず、変更なしに数える |
| 空欄のカテゴリの行の後の行 | 同じ曲に、空欄の行・カバーの行の順に一致 | 空欄の行はカテゴリを決めないため、カバーになる |
| 歌詞列の曲 | URLは登録されていないが、歌詞列の曲とタイトルが一致する行・作者が一致する行 | 新規作成せず、歌詞列の曲にURLを追加する |
| 歌詞列の曲と一致しない | 歌詞列の曲とタイトル・作者のどちらも異なる | スキップ |
| 歌詞列の曲と作者だけ一致し、short版かどうかが異なる | 作者の同じ「曲[short]」を指す、タイトルが「曲」の行 | 「歌詞列の曲とshort版かどうかが異なる」でスキップし、short版の曲にURLを追加しない |
| 歌詞列の曲と作者だけ一致し、どちらもshort版 | 作者の同じ「曲[Short]」を指す、タイトルが「曲[short]」の行 | 歌詞列の曲にURLを追加する |
| 歌詞列の曲が無い | 存在しない曲のidを指す | 新規作成する |
| 歌詞列の曲をユーザーが削除した（#1239） | 歌詞列が`is_removed=True`の曲を指し、URLは登録されていない | 「歌詞列の曲が削除されている」でスキップし、削除した曲を作り直さない |
| URLと歌詞列が別の曲 | URLは曲Aに、歌詞列は曲Bに一致 | URLで一致した曲Aを更新する |
| プレラの新規作成（#1064） | プ列が「年末プレラ５」・日付が2024年12月31日の行 | 曲の `prush` が「年末プレラ５」になり、プレラの `date` は2024年12月31日。Historyの `changes` に `["プレラ", "年末プレラ５"]` が入る |
| プレラの日付は最初に出てくる行の日付 | 2024年12月31日の「年末プレラ５」がある状態で、2024年12月30日のカテゴリ「企画」の行と、2025年1月1日の行 | 対象外のカテゴリの行の日付も使い、2024年12月30日になる（後の日付では変えない） |
| 日付の無いプレラ | 日付の無い行で作った「年末プレラ５」と、2025年1月1日のURLの無い（スキップする）行 | 2025年1月1日になる |
| 同じプレラの行 | プ列が同じ2行 | 2曲とも同じプレラになり、`Prush` は1件のみ |
| プレラの全角・半角 | 「年末プレラ３」が登録されている状態で、プ列が「年末プレラ3」の行 | 登録されている「年末プレラ３」を使い、`Prush` は増えない |
| 全角・半角だけが違うプレラが複数ある | 「年末プレラ３」、「年末プレラ3」の順に登録されている状態で、プ列が「年末プレラ3」の行 | 先に登録された「年末プレラ３」を使う（名前が完全に一致する方ではなく、idの小さい方） |
| プレラの追加 | プレラの無い曲に、プ列が「年末プレラ５」の行が一致 | 「曲のプレラを編集」のHistory（`["プレラ", "", "年末プレラ５"]`）を作る |
| プレラの付け替え | 「夏プレラ」の曲に、プ列が「晩夏プレラ6」の行が一致 | `prush` が「晩夏プレラ6」になり、`changes` に `["プレラ", "夏プレラ", "晩夏プレラ6"]` |
| 空欄のプ列 | 「夏プレラ」の曲に、プ列が空欄の行が一致 | プレラを消さず、変更なしに数える |
| 異なるプレラの複数の行に一致 | 「夏プレラ」の行・「晩夏プレラ6」の行が同じ曲に一致し、2回実行 | 最初の行の「夏プレラ」になり、Historyは1件のみ。「晩夏プレラ6」の `Prush` は作らない |
| スキップした行のプレラ | 掲載拒否の作者・プ列が「夏プレラ」の行 | スキップし、`Prush` を作らない |
| 編集者が削除されている | id=1のEditorが無い | id=1のEditorを作り、Historyの編集者にする |

#### 27-3. 年表の行の保存（`save_song_timelines`）（#1269）

| テストケース | 条件 | 期待結果 |
| --- | --- | --- |
| 新規作成した曲 | 2024年（`sheet_id=123`）の5行目・歌詞列が空 | `(2024, 123, 5, True)`の年表の行を作る（行のURLで作った曲のため、URL列で一致した行になる） |
| 更新・変更なしの曲 | 歌詞列にその曲のURLがある行で更新、歌詞列が空の行で変更なし | どちらも保存し、`is_lyrics_blank`はそれぞれ`False`・`True` |
| 歌詞列が空ではない | URLで一致した曲の行の歌詞列が別の曲のURL・ScratchのURL | `is_lyrics_blank=False`（「年表に登録する」にしない）。歌詞列の曲の年表の行は作らない |
| 歌詞列で一致した曲 | URLが登録されていない曲に、歌詞列（末尾に`/`のあるURL）がその曲を指す行が一致 | `is_lyrics_blank=False` |
| 複数の行に一致 | 2023年10行目（歌詞列が空）と2024年2行目（歌詞列あり）が同じ曲に一致 | 最初の行（2023年10行目、`is_lyrics_blank=True`）にする |
| スキップ・対象外のカテゴリの行 | 複数の曲に一致する行・カテゴリが「解読」の行 | 年表の行を作らない |
| 行の移動・歌詞列の追加 | 2行目（`is_lyrics_blank=True`）の年表の行がある曲が、歌詞列にその曲のURLがある3行目に一致 | 3行目・`is_lyrics_blank=False`に更新し、件数は増えない |
| 一致しなくなった曲 | 2024年の行に一致しなくなった曲と、2023年の年表の行がある曲で、2024年の行のみを取り込む | 2024年の曲の年表の行は削除し、2023年の年表の行は残す |

---

### 28. `lib/embed.py` — 曲ページの埋め込みプレイヤー（#1254）

**テストファイル**: `tests/test_lib_embed.py`

URLから、公式がiframeでの埋め込みに対応しているサービスの埋め込み用のURL（`src`）とiframeの形（`shape`。`video`: 16:9、`audio`: 高さ166px、`playlist`: 高さ300px、`scratch`: 485:402）を求める。埋め込めないURLは`None`を返す。URLの形が違う場合に別の動画を埋め込まないよう、サービスごとにホストとパスを確認し、IDは正規表現で確認した文字のみを`src`に使う（SoundCloudのみ`quote`でエンコードする）。X・Bluesky・TikTok・Misskeyなどは公式の埋め込みがスクリプトによるものか、URLだけでは埋め込み用のIDが分からないため対象外。Bandcampは埋め込み用の数値のIDが必要なため対象外。

#### 28-1. `get_embed(url)`

| テストケース | 入力 | 期待結果 |
| --- | --- | --- |
| YouTube | `https://youtu.be/dQw4w9WgXcQ`・`youtube.com/watch?v=…&t=30`・`youtube.com/shorts/…` | `https://www.youtube-nocookie.com/embed/<動画ID>`・`video` |
| 他のサイトのクエリのYouTube | `https://x.com/user/status/1?u=https://youtu.be/dQw4w9WgXcQ` | `None`（ホストがYouTubeではない） |
| YouTubeのチャンネル | `https://www.youtube.com/@subekashi` | `None` |
| ニコニコ動画 | `https://nicovideo.jp/watch/sm12345678`・`nm1`・`so1`・数字のみ・`www.`・`sp.`・クエリ付き | `https://embed.nicovideo.jp/watch/<動画ID>`（クエリは付けない）・`video` |
| ニコニコ動画の動画以外 | `nicovideo.jp/user/…`・`/mylist/…`・`/watch/`・`/watch/sm12345abc` | `None` |
| SoundCloudの曲 | `https://soundcloud.com/artist/track-name` | `https://w.soundcloud.com/player/?url=https%3A%2F%2Fsoundcloud.com%2Fartist%2Ftrack-name&visual=false`・`audio` |
| SoundCloudのプレイリスト | `https://soundcloud.com/artist/sets/album-name` | 同様の`src`・`playlist` |
| SoundCloudのクエリ・末尾のスラッシュ・モバイル | `…/track-name/?si=abc&utm_source=clipboard`・`m.soundcloud.com` | クエリ・スラッシュを除いた`https://soundcloud.com/…`を`url`に指定した`src` |
| SoundCloudのパーセントエンコード | `https://soundcloud.com/artist/%E6%9B%B2` | `url`の`%`を`%25`にエンコードする（プレーヤーが1回デコードして元のURLに戻る） |
| SoundCloudのユーザーのページ・タブ | `soundcloud.com/artist`・`/tracks`・`/sets`・`/likes`・`/track-name/recommended`・`soundcloud.com/` | `None` |
| SoundCloudの短縮URL | `https://on.soundcloud.com/d3pgp` | `None`（プレーヤーが「有効なSoundCloudのURLではない」と表示する。Playwrightで確認） |
| ビリビリ動画 | `https://bilibili.com/video/BV1qV411J7Kq`・`?p=3`・`www.`・`/?spm_id_from=333&p=2` | `https://player.bilibili.com/player.html?isOutside=true&bvid=<BV番号>&p=<パート>&autoplay=0`（パートの既定は1）・`video` |
| ビリビリ動画のav番号 | `https://bilibili.com/video/av170001` | BV番号（`BV17x411w7KC`）に変換した`src` |
| ビリビリ動画の動画以外 | `bilibili.com/read/cv123`・`space.bilibili.com/123` | `None` |
| Google Drive | `https://drive.google.com/file/d/<ID>/view?usp=sharing`・`/file/u/0/d/<ID>/view` | `https://drive.google.com/file/d/<ID>/preview`・`video` |
| Google Driveのフォルダ | `https://drive.google.com/drive/folders/<ID>` | `None` |
| Scratch | `https://scratch.mit.edu/projects/123456789`・`/editor` | `https://scratch.mit.edu/projects/<ID>/embed`・`scratch` |
| Scratchの作品以外 | `scratch.mit.edu/users/someone`・`/studios/123` | `None` |
| 対応していないサービス | X・Bandcamp・Bluesky・ピアプロ・BOOTH | `None` |
| 空文字・URLではない文字列・`javascript:`のURL | `""`・`"not a url"`・`javascript:alert(1)//youtu.be/dQw4w9WgXcQ` | `None` |

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
├── test_lib_song_filterset.py      # 実装済み: 作者ページの並び替え
├── test_forms.py                   # 実装済み: フォームバリデーション
├── test_views.py                   # 実装済み: ビュー（GET・POST）
├── test_api.py                     # 実装済み: REST API
├── test_middleware.py              # 実装済み: ミドルウェア
├── test_security.py                # 実装済み: CSP・CORS・CSRFトークン・SRI（結合、#1126）
├── test_models.py                  # 実装済み: モデル基本動作
├── test_converters.py              # 実装済み: URLコンバータ
├── test_lib_youtube.py             # 実装済み: YouTube Data API連携
├── test_lib_timeline.py            # 実装済み: すべあな界隈年表の読み取り
├── test_lib_timeline_import.py     # 実装済み: すべあな界隈年表からの曲の登録・更新
├── test_lib_ogp.py                 # 実装済み: ページごとのOGP画像
├── test_lib_ip.py                  # 実装済み: クライアントのIP
├── test_lib_embed.py               # 実装済み: 曲ページの埋め込みプレイヤー
├── test_management_commands.py     # 実装済み: 管理コマンド
├── test_templatetags_song_card.py  # 実装済み: song_card テンプレートタグ
├── test_templatetags_ogp.py        # 実装済み: ogp テンプレートタグ
└── test_templatetags_changes.py    # 実装済み: changes テンプレートタグ

article/
└── tests.py                        # 実装済み: ArticlesView・DefaultArticleView
```

## 今後の課題

- **`SongEditView` POST テスト** (`test_views.py` への追加)
  - 正常時のリダイレクト先・バリデーションエラー時の再表示（YouTube API 呼び出しのモック化が必要）
