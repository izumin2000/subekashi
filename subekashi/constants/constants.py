DEFAULT_DESCRIPTION = "全て歌詞の所為です。は界隈曲をまとめたサイトです。"

CONST_ERROR = "エラー：python manage.py constを実行してください"

ASIDE_PAGES = [
    {
        "url": "subekashi:top",
        "name": "トップ",
        "icon": "fas fa-home"
    },
    {
        "url": "subekashi:song_new",
        "name": "新規登録",
        "icon": "fa fa-plus"
    },
    {
        "url": "subekashi:songs",
        "name": "検索",
        "icon": "fas fa-search"
    },
    {
        "url": "subekashi:ai",
        "name": "歌詞生成",
        "icon": "fa fa-robot"
    },
    {
        "url": "subekashi:ad",
        "name": "宣伝",
        "icon": "fas fa-bullhorn"
    },
    {
        "url": "subekashi:special",
        "name": "スペシャル",
        "icon": "far fa-star"
    },
    {
        "url": "subekashi:contact",
        "name": "お問い合わせ",
        "icon": "fas fa-envelope"
    },
    {
        "url": "subekashi:setting",
        "name": "設定",
        "icon": "fas fa-cog"
    }
]

DEFALT_ICON = "<i class='fas fa-globe'></i>"

URL_ICON = {
    r"(?:^|\.)youtu\.be$": "<i class='fab fa-youtube'></i>",
    r"(?:^|\.)youtube\.com$": "<i class='fab fa-youtube'></i>",
    r"(?:^|\.)soundcloud\.com$": "<i class='fab fa-soundcloud'></i>",
    r"(?:^|\.)x\.com$": "<i class='fab fa-twitter'></i>",
    r"(?:^|\.)twitter.com$": "<i class='fab fa-twitter'></i>",
    r"(?:^|\.)bandcamp.com$": "<i class='fab fa-bandcamp'></i>",
    r"drive\.google\.com": "<i class='fab fa-google-drive'></i>",
    r"(?:^|\.)nicovideo\.jp$": f"<img src='/static/subekashi/image/niconico.png' alt='ニコニコ動画'></img>",
    r"(?:^|\.)bilibili\.com$": f"<img src='/static/subekashi/image/bilibili.png' alt='ビリビリ動画'></img>",
    r"imicomweb\.com": f"<img src='/static/subekashi/image/imicomweb.png' alt='イミコミュ'></img>",
    r"scratch\.mit\.edu": "<i class='fas fa-cat'></i>",
    r"linkco\.re": "<i class='fas fa-align-justify'></i>",
}

# サービス名に対応するURL,アイコン,名前
URLS = {
    "youtube":([r"youtube\.com",r"youtu\.be"],"<i class='fab fa-youtube'></i>","Youtube"),
    "soundcloud":([r"soundcloud\.com"],"<i class='fab fa-soundcloud'></i>","SoundCloud"),
    "twitter":([r"x\.com",r"twitter.com"],"<i class='fab fa-twitter'></i>","Twitter"),
    "bandcamp":([r"bandcamp.com"],"<i class='fab fa-bandcamp'></i>","BandCamp"),
    "googledrive":([r"drive\.google\.com"],"<i class='fab fa-google-drive'></i>","Google Drive"),
    "niconico":([r"nicovideo\.jp"],f"<img src='/static/subekashi/image/niconico.png' alt='ニコニコ動画'></img>","ニコニコ動画"),
    "bilibili":([r"bilibili\.com"],f"<img src='/static/subekashi/image/bilibili.png' alt='ビリビリ動画'></img>","BiliBili"),
    "imicomweb":([r"imicomweb\.com"], f"<img src='/static/subekashi/image/imicomweb.png' alt='イミコミュ'></img>","イミコミュ"),
    "scratch":([r"scratch\.mit\.edu"],"<i class='fas fa-cat'></i>","Scratch"),
    "linkcore":([r"linkco\.re"],"<i class='fas fa-align-justify'></i>","Linkcore")
}

SAFE_DOMAINS = list(URL_ICON.keys())