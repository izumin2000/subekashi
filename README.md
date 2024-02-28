# 全て歌詞の所為です。とは  
『全て歌詞の所為です。』とは「[界隈曲](https://dic.nicovideo.jp/a/%E7%95%8C%E9%9A%88%E6%9B%B2)」と呼ばれる音楽ジャンルに焦点を当てた界隈曲情報掲載サイトです。
以下のような機能があります。
- 界隈曲の情報の掲載機能
- 界隈曲の情報の閲覧機能
- 界隈曲の情報の検索機能
- 界隈曲の歌詞の生成機能(正常に狂うのです。/ 全て蛇の目の所為です。)
- 界隈曲の宣伝機能(すべ歌詞DSP)
- 設定機能

# 起動方法
1. 必要パッケージの用意
```
pip install -r requirements.txt
```

2. マイグレーション
```
python manage.py makemigrations
python manage.py migrate
```

3. local_settings.pyの設定
以下のコードを実行し鍵を生成します。
```py
from django.core.management.utils import get_random_secret_key
get_random_secret_key()
```
その後、local_settings.pyの変数`SECRET_KEY`に`get_random_secret_key()`で取得した値を入力します。
また必要に応じて、local_settings.pyにDiscordの連携サービスウェブフックのURLを登録してください。

4. サーバー起動
```
python manage.py runserver
```

5. アクセス  
[http://subekashi.localhost:8000/](http://subekashi.localhost:8000/) にアクセスとアプリの画面が表示されます。


# 全て歌詞の所為です。APIについて  
全て歌詞の所為です。上で登録された情報はRESTfulなAPIで提供しています。  

[https://lyrics.imicomweb.com/api/song](https://lyrics.imicomweb.com/api/song)：全て歌詞の所為です。に登録された曲の情報です。GET, HEAD, OPTIONSのみ受け付けています。

[https://lyrics.imicomweb.com/api/ad](https://lyrics.imicomweb.com/api/ad)：全て歌詞の所為です。に登録された宣伝の情報です。GET, HEAD, OPTIONSとPUTのうちカラムviewとカラムclickの値の変更のみ受け付けています。

[https://lyrics.imicomweb.com/api/ai](https://lyrics.imicomweb.com/api/ai)：正常に狂うのです。が生成した歌詞の情報です。GET, HEAD, OPTIONSとPUTのうちカラムscoreの変更のみ受け付けています。


# リンク集
- [全て歌詞の所為です。](https://lyrics.imicomweb.com/)

- [全て歌詞の所為です。 YouTube](https://www.youtube.com/@subekashi)

- [全て歌詞の所為です。 X](https://twitter.com/subekashi)


# クレジット
© 2024 全てあなたの所為です。

本ソフトでは表示フォントに「源全角ゴ改」(https://drive.google.com/drive/folders/19WidrJoCmI5qLJV-eR_ydURIwxB2-DS) を使用しています。
Licensed under SIL Open Font License 1.1 http://scripts.sil.org/OFL
© 2021 全て語り手の所為です。

本ソフトでは表示フォントに「Noto Sans JP」(https://fonts.google.com/selection?query=noto) を使用しています。
Licensed under SIL Open Font License 1.1 http://scripts.sil.org/OFL
© 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'