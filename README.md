# 全て歌詞の所為です。 README

## 全て歌詞の所為です。とは  
『全て歌詞の所為です。』とは「[界隈曲](https://dic.nicovideo.jp/a/%E7%95%8C%E9%9A%88%E6%9B%B2)」と呼ばれる音楽ジャンルに焦点を当てた界隈曲情報掲載サイトです。  
以下のような機能があります。

- 界隈曲の情報の掲載機能
- 界隈曲の情報の閲覧機能
- 界隈曲の情報の検索機能
- 界隈曲の歌詞の生成機能(正常に狂うのです。/ 全て蛇の目の所為です。)
- 界隈曲の宣伝機能(すべかしDSP)
- 設定機能

## セットアップ方法

1\. 前提条件
gitコマンドとpythonコマンドが使えることが前提です。  
  
2\. クローン

```bash
git clone https://github.com/izumin2000/subekashi.git --depth 1
```

3\. カレントディレクトリの変更

```bash
cd subekashi
```
  
4\. 仮想環境の作成（必要に応じて）

pythonのvenvを利用して仮想環境`.env`を作成します。  

```bash
python -m venv .env
```
  
5\. 仮想環境の起動（必要に応じて）  

```bash
.env/Scripts/activate.ps1;
```
  
6\. ライブラリのインストール  

```bash
pip install -r requirements.txt
```
  
7\. local_setting.pyの作成  

```bash
cp config/local_settings_sample.py config/local_settings.py
```
※ cpコマンドを利用できない場合は、別のファイルをコピーするコマンドかエクスプローラーを利用してください。
  
8\. シェルの起動  

```bash
python manage.py shell
```
  
9\. 鍵の生成  
以下のpythonコードを実行して鍵を生成します。  
鍵の値はコピーしてください。  

```py
from django.core.management.utils import get_random_secret_key
get_random_secret_key()
quit()
```

`quit()`実行時にエラーが出力されることがありますが、気にしなくて大丈夫です。  
  
10\. local_settings.pyの設定  
`config/local_settings.py`を開き、コピーした値を`SECRET_KEY`に代入します。

```py
SECRET_KEY = "=*************************************************"
```
  
11\. マイグレーション  

```bash
python manage.py makemigrations
python manage.py migrate
```

12\. データベースの初期値の設定  
マイグレーションした直後はデータベースにデータが入っておらずエラーになる処理がある為、以下のコマンドを実行して初期値を追加します。  

```bash
python manage.py loaddata songs.json
```

初期値には全てあなたの所為です。の全曲と『12』・『15』・『17』が登録されています。  
  
13\. 定数ファイルの作成（必要に応じて）  
全て歌詞の所為です。では高頻度で変わる定数ファイルを.gitignore対象で`subekashi/constants/dynamic`に保存しております。  
必要に応じて以下のコマンドを実行して定数ファイルを生成してください。  

```bash
python manage.py const
```
  
## 起動方法  

1\. 仮想環境の起動（venvを利用している場合）  
仮想環境`.env`を起動します。  

```bash
.env/Scripts/activate.ps1;
```
  
2\. サーバー起動  

```bash
python manage.py runserver
```
  
3\. アクセス  
[http://subekashi.localhost:8000/](http://subekashi.localhost:8000/) にアクセスとアプリの画面が表示されます。  
エラーが発生した場合はissueで報告してください。  
  
## 全て歌詞の所為です。APIについて
全て歌詞の所為です。上で登録された情報はRESTfulなAPIで提供しています。

### Song API
**エンドポイント**: [https://lyrics.imicomweb.com/api/song](https://lyrics.imicomweb.com/api/song)
**メソッド**: GET, HEAD, OPTIONS
**レート制限**: 2リクエスト/秒

全て歌詞の所為です。に登録された曲の情報を取得できます。

#### クエリパラメータ

**テキスト検索（部分一致、大文字小文字を区別しない）**
- `title`: 曲名で検索（最大500文字）
- `author`: 作者名で検索（最大500文字）
- `lyrics`: 歌詞で検索（最大10000文字）
- `url`: URLで検索（最大500文字）
  - 自動的にURLが正規化されます（YouTubeの短縮、クエリパラメータの削除など）
- `keyword`: タイトル、作者、歌詞、URLを横断検索（最大500文字）
  - 自動的にURLが正規化されます

**完全一致検索**
- `title_exact`: 曲名で完全一致検索（最大500文字）
- `author_exact`: 作者名で完全一致検索（最大500文字）

**数値範囲フィルタ（1以上の値のみ）**
- `view_gte`: 視聴回数の下限（1以上の整数）
- `view_lte`: 視聴回数の上限（1以上の整数）
- `like_gte`: いいね数の下限（1以上の整数）
- `like_lte`: いいね数の上限（1以上の整数）

**日時範囲フィルタ**
- `upload_time_gte`: アップロード日時の下限（ISO 8601形式）
- `upload_time_lte`: アップロード日時の上限（ISO 8601形式）

**真偽値フィルタ**
- `issubeana`: すべあな曲かどうか
- `isjoke`: ネタ曲かどうか
- `isdraft`: 下書きかどうか
- `isoriginal`: オリジナル模倣曲かどうか
- `isinst`: インスト曲かどうか
- `isdeleted`: 削除済みかどうか
- `islack`: 不完全な曲（情報が欠けている曲）

**特殊フィルタ**
- `imitate`: 模倣元（カンマ区切りで複数指定可、最大10000文字）
- `imitated`: 被模倣（カンマ区切りで複数指定可、最大10000文字）
- `guesser`: 候補（タイトルとチャンネルを検索、最大500文字）
- `mediatypes`: メディアタイプ（正規表現対応、最大100文字）

**ページネーション**
- `page`: ページ番号（デフォルト: 1、最小: 1）
- `size`: 1ページあたりの件数（デフォルト: 50、最小: 1）

**ソート**
- `sort`: ソート順を指定
  - 利用可能な値: `id`, `-id`, `title`, `-title`, `author`, `-author`, `upload_time`, `-upload_time`, `view`, `-view`, `like`, `-like`, `post_time`, `-post_time`, `random`
  - `-`を付けると降順、付けないと昇順
  - `id`は登録日時順（登録が古い順）、`-id`は登録が新しい順
  - `random`を指定するとランダムソート

**注意事項**
- YouTube関連のフィルタ（view, like, upload_time）やソートを使用する場合、`mediatypes`を指定しない限り、自動的にYouTube動画のみに絞り込まれます
- view関連のフィルタまたはソートを使用する場合、view >= 1 の曲のみが対象となります
- like関連のフィルタまたはソートを使用する場合、like >= 1 の曲のみが対象となります
- view、likeの値は1以上の整数のみ受け付けます。0以下の値を指定するとバリデーションエラーが発生します
- バリデーションエラーが発生した場合、400 Bad Requestと共にエラーメッセージが返されます

#### レスポンス形式

**一覧取得時**
```json
{
  "count": 100,
  "page": 1,
  "size": 50,
  "max_page": 2,
  "result": [
    {
      "id": 1,
      "title": "曲名",
      "authors": [
        {
          "id": 1,
          "name": "作者"
        },
        ...
      ],
      ...
    }
  ]
}
```

- `count`: 検索条件に一致する曲の総数
- `page`: 現在のページ番号
- `size`: 1ページあたりの件数
- `max_page`: 最大ページ数
- `result`: 曲のリスト

**個別取得時（/api/song/{song_id}）**
```json
{
  "song_id": 1,
  "title": "曲名",
  "authors": [
    {
      "id": 1,
      "name": "作者"
    },
    ...
  ],
  ...
}
```

### Ad API
**エンドポイント**: [https://lyrics.imicomweb.com/api/ad](https://lyrics.imicomweb.com/api/ad)
**メソッド**: GET, HEAD, OPTIONS, PUT, PATCH

全て歌詞の所為です。に登録された宣伝の情報を取得・更新できます。

- **GET**: 宣伝情報の取得
- **PUT/PATCH**: `view`（閲覧数）と`click`（クリック数）フィールドのみ更新可能
  - これら以外のフィールドを更新しようとするとバリデーションエラーが返されます
- **POST/DELETE**: 使用不可

### AI API
**エンドポイント**: [https://lyrics.imicomweb.com/api/ai](https://lyrics.imicomweb.com/api/ai)
**メソッド**: GET, HEAD, OPTIONS, PUT, PATCH

正常に狂うのです。が生成した歌詞の情報を取得・更新できます。

- **GET**: AI生成歌詞の取得
- **PUT/PATCH**: `score`（評価スコア）フィールドのみ更新可能
  - このフィールド以外を更新しようとするとバリデーションエラーが返されます
- **POST/DELETE**: 使用不可

## コントリビューション
全て歌詞の所為です。ではプルリクエストを積極的に受け入れています。  
主に以下のことをやっていただけると嬉しいです。  

- スペシャルデザインの追加
- バグの修正
- issueの内容
  - 具体的な内容については、コメントしてくれたら回答します。
  - assigneeが私のissueでも、相談していただけたら、担当することができるかもです。

その他、issueの起票だけでも助かります。  
マージの場所はmainでお願いします。  
PRにはClaude Code Actionsを使用しております。  

## リンク集

- [全て歌詞の所為です。](https://lyrics.imicomweb.com/)

- [全て歌詞の所為です。 YouTube](https://www.youtube.com/@subekashi)

- [全て歌詞の所為です。 YouTube サブ](https://www.youtube.com/@lyricsokiba)

- [全て歌詞の所為です。 X](https://x.com/subekashi)

- [全て歌詞の所為です。 X サブ](https://x.com/lyricsokiba)

## クレジット
本ソフトでは表示フォントに「源全角ゴ改」(<https://drive.google.com/drive/folders/19WidrJoCmI5qLJV-eR_ydURIwxB2-DS>) を使用しています。
Licensed under SIL Open Font License 1.1 <http://scripts.sil.org/OFL>
© 2021 全て語り手の所為です。

本ソフトでは表示フォントに「Noto Sans JP」(<https://fonts.google.com/selection?query=noto>) を使用しています。
Licensed under SIL Open Font License 1.1 <http://scripts.sil.org/OFL>
© 2014-2021 Adobe (<http://www.adobe.com/>), with Reserved Font Name 'Source'