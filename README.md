# 全て歌詞の所為です。とは  
『全て歌詞の所為です。』とは「[界隈曲](https://dic.nicovideo.jp/a/%E7%95%8C%E9%9A%88%E6%9B%B2)」と呼ばれる音楽ジャンルに焦点を当てた界隈曲情報掲載サイトです。  
以下のような機能があります。
- 界隈曲の情報の掲載機能
- 界隈曲の情報の閲覧機能
- 界隈曲の情報の検索機能
- 界隈曲の歌詞の生成機能(正常に狂うのです。/ 全て蛇の目の所為です。)
- 界隈曲の宣伝機能(すべかしDSP)
- 設定機能

# セットアップ方法
0. 前提条件  
gitコマンドとpythonコマンドが使えることが前提です。  
  
1. クローン  
```
git clone https://github.com/izumin2000/subekashi.git --depth 1
```
  
2. カレントディレクトリの変更  
```
cd subekashi
```
  
3. 仮想環境の作成（必要に応じて）  
pythonのvenvを利用して仮想環境`.env`を作成します。  
```
python -m venv .env
```
  
4. 仮想環境の起動（必要に応じて）  
```
.env/Scripts/activate.ps1;
```
  
5. ライブラリのインストール  
```
pip install -r requirements.txt
```
  
6. local_setting.pyの作成  
```
cp config/local_settings_sample.py config/local_settings.py
```
  
7. シェルの起動  
```
python manage.py shell
```
  
8. 鍵の生成  
以下のpythonコードを実行して鍵を生成します。  
鍵の値はコピーしてください。  
```py
from django.core.management.utils import get_random_secret_key
get_random_secret_key()
quit()
```
`quit()`実行時にエラーが出力されることがありますが、気にしなくて大丈夫です。  
  
9. local_settings.pyの設定  
`lib/local_settings.py`を開き、コピーした値を`SECRET_KEY`に代入します。    
```py
SECRET_KEY = "=*************************************************"
```
  
10. マイグレーション  
```
python manage.py makemigrations
python manage.py migrate
```

11. データベースの初期値の設定  
マイグレーションした直後はデータベースにデータが入っておらずエラーになる処理がある為、以下のコマンドを実行して初期値を追加します。  
```
python manage.py loaddata songs.json
```
初期値には全てあなたの所為です。の全曲と『12』・『15』・『17』が登録されています。  
  
12. 定数ファイルの作成（必要に応じて）  
全て歌詞の所為です。では高頻度で変わる定数ファイルを.gitignore対象で`subekashi/constants/dynamic`に保存しております。  
必要に応じて以下のコマンドを実行して定数ファイルを生成してください。  
```
python manage.py const
```
  
# 起動方法  
1. 仮想環境の起動（venvを利用している場合）  
仮想環境`.env`を起動します。  
```
.env/Scripts/activate.ps1;
```
  
2. サーバー起動  
```
python manage.py runserver
```
  
3. アクセス  
[http://subekashi.localhost:8000/](http://subekashi.localhost:8000/) にアクセスとアプリの画面が表示されます。  
エラーが発生した場合はissueで報告してください。  
  
# 全て歌詞の所為です。APIについて  
全て歌詞の所為です。上で登録された情報はRESTfulなAPIで提供しています。  

[https://lyrics.imicomweb.com/api/song](https://lyrics.imicomweb.com/api/song)：全て歌詞の所為です。に登録された曲の情報です。GET, HEAD, OPTIONSのみ受け付けています。

[https://lyrics.imicomweb.com/api/ad](https://lyrics.imicomweb.com/api/ad)：全て歌詞の所為です。に登録された宣伝の情報です。GET, HEAD, OPTIONSとPUTのうちカラムviewとカラムclickの値の変更のみ受け付けています。

[https://lyrics.imicomweb.com/api/ai](https://lyrics.imicomweb.com/api/ai)：正常に狂うのです。が生成した歌詞の情報です。GET, HEAD, OPTIONSとPUTのうちカラムscoreの変更のみ受け付けています。


# コントリビューション
現在、個人的にバックエンドのリファクタリングを行っております。  
その関係上、主にフロントエンド周りを中心にコントリビューションをしていただけると嬉しいです。  
特に`id`と`class`の命名規則をケバブケースにする[イシュー](https://github.com/izumin2000/subekashi/issues/316)を行っていただけると嬉しいです。

# リンク集
- [全て歌詞の所為です。](https://lyrics.imicomweb.com/)

- [全て歌詞の所為です。 YouTube](https://www.youtube.com/@subekashi)

- [全て歌詞の所為です。 X](https://twitter.com/subekashi)


# クレジット
本ソフトでは表示フォントに「源全角ゴ改」(https://drive.google.com/drive/folders/19WidrJoCmI5qLJV-eR_ydURIwxB2-DS) を使用しています。
Licensed under SIL Open Font License 1.1 http://scripts.sil.org/OFL
© 2021 全て語り手の所為です。

本ソフトでは表示フォントに「Noto Sans JP」(https://fonts.google.com/selection?query=noto) を使用しています。
Licensed under SIL Open Font License 1.1 http://scripts.sil.org/OFL
© 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'