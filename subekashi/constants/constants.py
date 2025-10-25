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
        "url": "article:articles",
        "name": "記事",
        "icon": "fas fa-book"
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

ALLOW_MEDIAS = [
    {
        "id": "youtube",
        "name": "YouTube",
        "regex": r"(^|.)youtu.be",
        "icon": "<i class='fab fa-youtube'></i>",
    },
    {
        "id": "x",
        "name": "X",
        "regex": r"(^|.)x.com",
        "icon": "<i class='fab fa-twitter'></i>",
    },
    {
        "id": "nicovideo",
        "name": "ニコニコ動画",
        "regex": r"(^|.)nicovideo.jp",
        "icon": "<img src='/static/subekashi/image/niconico.png' alt='ニコニコ動画'></img>",
    },
    {
        "id": "soundcloud",
        "name": "SoundCloud",
        "regex": r"(^|.)soundcloud.com",
        "icon": "<i class='fab fa-soundcloud'></i>",
    },
    {
        "id": "scratch",
        "name": "Scratch",
        "regex": r"scratch.mit.edu",
        "icon": "<i class='fas fa-cat'></i>",
    },
    {
        "id": "bandcamp",
        "name": "Bandcamp",
        "regex": r"(^|.)bandcamp.com",
        "icon": "<i class='fab fa-bandcamp'></i>",
    },
    {
        "id": "drive",
        "name": "Google Drive",
        "regex": r"drive.google.com",
        "icon": "<i class='fab fa-google-drive'></i>",
    },
    {
        "id": "bilibili",
        "name": "ビリビリ動画",
        "regex": r"(^|.)bilibili.com",
        "icon": "<img src='/static/subekashi/image/bilibili.png' alt='ビリビリ動画'></img>",
    },
    {
        "id": "imicom",
        "name": "イミコミュ",
        "regex": r"imicomweb.com",
        "icon": "<img src='/static/subekashi/image/imicomweb.png' alt='イミコミュ'></img>",
    },
    {
        "id": "linkcore",
        "name": "LinkCore",
        "regex": r"linkco.re",
        "icon": "<i class='fas fa-align-justify'></i>",
    },
    {
        "id": "bandlab",
        "name": "Bandlab",
        "regex": r"bandlab.com",
        "icon": "<i class='fas fa-flask'></i>",
    },
    {
        "id": "newgrounds",
        "name": "ニューグラウンズ",
        "regex": r"newgrounds.com",
        "icon": "<i class='fas fa-gamepad'></i>",
    },
    {
        "id": "note",
        "name": "note",
        "regex": r"note.com",
        "icon": "<i class='fas fa-book'></i>",
    },
]

ALL_MEDIAS = ALLOW_MEDIAS + [
    {
        "id": "other", 
        "name": "URL未登録",
        "regex": r"^$",
        "icon": "<i class='fas fa-unlink'></i>"
    },
    {
        "id": "disallow", 
        "name": "許可されていないURL",
        "regex": r".*",
        "icon": "<i class='fas fa-exclamation-triangle'></i>"
    }
]