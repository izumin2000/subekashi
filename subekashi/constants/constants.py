DEFAULT_DESCRIPTION = "全て歌詞の所為です。は界隈曲をまとめたサイトです。"

CONST_ERROR = "エラー：python manage.py constを実行してください"

# BANされた編集者（Editor.is_banned）が、ページの読み取り以外の操作をしたときに表示する（#1281）
# フォームの送信では、base.htmlのdata-banned-messageで受け取ったbase.jsがトーストを表示する
BANNED_ERROR = "処理を完了できませんでした。"

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
        "url": "subekashi:histories",
        "name": "編集履歴",
        "icon": "fas fa-history"
    },
    {
        "url": "subekashi:ai",
        "name": "歌詞作成",
        "icon": "fas fa-align-center"
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
        "url": "subekashi:stats",
        "name": "統計",
        "icon": "fas fa-chart-line"
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
        "regex": r"(^|[./])youtu\.be($|[/:?#])",
        "icon": "<i class='fab fa-youtube'></i>",
    },
    {
        "id": "x",
        "name": "X",
        "regex": r"(^|[./])x\.com($|[/:?#])",
        "icon": "<i class='fab fa-twitter'></i>",
    },
    {
        "id": "nicovideo",
        "name": "ニコニコ動画",
        "regex": r"(^|[./])nicovideo\.jp($|[/:?#])",
        "icon": "<img src='/static/subekashi/image/niconico.png' alt='ニコニコ動画'></img>",
    },
    {
        "id": "soundcloud",
        "name": "SoundCloud",
        "regex": r"(^|[./])soundcloud\.com($|[/:?#])",
        "icon": "<i class='fab fa-soundcloud'></i>",
    },
    {
        "id": "vimesis",
        "name": "Vimesis",
        "regex": r"(^|[./])vimesis\.com($|[/:?#])",
        "icon": "<i class='fas fa-address-book'></i>",
    },
    {
        "id": "scratch",
        "name": "Scratch",
        "regex": r"(^|[./])scratch\.mit\.edu($|[/:?#])",
        "icon": "<i class='fas fa-cat'></i>",
    },
    {
        "id": "bandcamp",
        "name": "Bandcamp",
        "regex": r"(^|[./])bandcamp\.com($|[/:?#])",
        "icon": "<i class='fab fa-bandcamp'></i>",
    },
    {
        "id": "drive",
        "name": "Google Drive",
        "regex": r"(^|[./])drive\.google\.com($|[/:?#])",
        "icon": "<i class='fab fa-google-drive'></i>",
    },
    {
        "id": "bilibili",
        "name": "ビリビリ動画",
        "regex": r"(^|[./])bilibili\.com($|[/:?#])",
        "icon": "<img src='/static/subekashi/image/bilibili.png' alt='ビリビリ動画'></img>",
    },
    {
        "id": "imicom",
        "name": "イミコミュ",
        "regex": r"(^|[./])imicomweb\.com($|[/:?#])",
        "icon": "<img src='/static/subekashi/image/imicomweb.png' alt='イミコミュ'></img>",
    },
    {
        "id": "linkcore",
        "name": "LinkCore",
        "regex": r"(^|[./])linkco\.re($|[/:?#])",
        "icon": "<i class='fas fa-align-justify'></i>",
    },
    {
        "id": "bandlab",
        "name": "Bandlab",
        "regex": r"(^|[./])bandlab\.com($|[/:?#])",
        "icon": "<i class='fas fa-flask'></i>",
    },
    {
        "id": "newgrounds",
        "name": "ニューグラウンズ",
        "regex": r"(^|[./])newgrounds\.com($|[/:?#])",
        "icon": "<i class='fas fa-gamepad'></i>",
    },
    {
        "id": "note",
        "name": "note",
        "regex": r"(^|[./])note\.com($|[/:?#])",
        "icon": "<i class='fas fa-book'></i>",
    },
    {
        "id": "TikTok",
        "name": "tiktok",
        "regex": r"(^|[./])tiktok\.com($|[/:?#])",
        "icon": "<i class='fab fa-tiktok'></i>",
    },
    {
        "id": "vidlii",
        "name": "VidLii",
        "regex": r"(^|[./])vidlii\.com($|[/:?#])",
        "icon": "<i class='fas fa-caret-square-down'></i>",
    },
    {
        "id": "bluesky",
        "name": "Bluesky",
        "regex": r"(^|[./])bsky\.app($|[/:?#])",
        "icon": "<img src='/static/subekashi/image/bluesky.png' alt='Bluesky'></img>",
    },
    {
        "id": "bowlroll",
        "name": "BowlRoll",
        "regex": r"(^|[./])bowlroll\.net($|[/:?#])",
        "icon": "<i class='fas fa-file-download'></i>",
    },
    {
        "id": "misskey",
        "name": "Misskey.io",
        "regex": r"(^|[./])misskey\.io($|[/:?#])",
        "icon": "<i class='fas fa-comment-dots'></i>",
    },
    {
        "id": "booth",
        "name": "BOOTH",
        "regex": r"(^|[./])booth\.pm($|[/:?#])",
        "icon": "<i class='fas fa-store'></i>",
    },
    {
        "id": "piapro",
        "name": "ピアプロ",
        "regex": r"(^|[./])piapro\.jp($|[/:?#])",
        "icon": "<i class='fas fa-headphones'></i>",
    },
    {
        "id": "rechord",
        "name": "rechord",
        "regex": r"(^|[./])rechord\.cc($|[/:?#])",
        "icon": "<i class='fas fa-guitar'></i>",
    },
    {
        "id": "dropbox",
        "name": "Dropbox",
        "regex": r"(^|[./])dropbox\.com($|[/:?#])",
        "icon": "<i class='fab fa-dropbox'></i>",
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

# 曲のフラグ（曲ページのタグ・曲カードのアイコン、#1228）。曲ページ・曲カードともにこの順に並べる
# name: Songのフィールド名。is_lack（未完成）とis_xx（非すべあな模倣曲）はSong.get_flags()で求める
# query: 曲ページのタグから検索画面に移るときのクエリ（Noneならリンクにしない）
# tutorial: 曲ページのタグに付ける説明（data-tutorial）
SONG_FLAGS = [
    {'name': 'is_questionable', 'icon': 'fas fa-question', 'label': '界隈曲?', 'query': None, 'tutorial': 'is_questionable'},
    {'name': 'is_lack', 'icon': 'fas fa-tasks', 'label': '未完成', 'query': 'is_lack=True', 'tutorial': None},
    {'name': 'is_draft', 'icon': 'fas fa-user-edit', 'label': '下書き', 'query': 'is_draft=True', 'tutorial': None},
    {'name': 'is_original', 'icon': 'fas fa-external-link-alt', 'label': 'オリジナル模倣', 'query': 'is_original=True', 'tutorial': None},
    {'name': 'is_joke', 'icon': 'far fa-meh-rolling-eyes', 'label': 'ネタ曲', 'query': 'is_joke=only', 'tutorial': None},
    {'name': 'is_inst', 'icon': 'fas fa-comment-slash', 'label': 'インスト曲', 'query': 'is_inst=True', 'tutorial': None},
    {'name': 'is_xx', 'icon': 'fas fa-fish', 'label': '非すべあな模倣曲', 'query': 'is_subeana=xx', 'tutorial': None},
    {'name': 'is_deleted', 'icon': 'far fa-eye-slash', 'label': '非公開/削除済み', 'query': 'is_deleted=True', 'tutorial': None},
    {'name': 'is_special', 'icon': 'fas fa-magic', 'label': 'スペシャルデザイン', 'query': None, 'tutorial': None},
    {'name': 'is_limited', 'icon': 'fas fa-low-vision', 'label': '限定公開', 'query': None, 'tutorial': 'is_limited'},
]

# 曲のカテゴリ（#423）。Song.CHOICESはこの順・表示名で作る
# icon: 曲ページのタグ・模倣の一覧と、検索画面のカテゴリのフォームのアイコン
SONG_CATEGORIES = [
    {'value': 'song', 'label': '曲', 'icon': 'fas fa-music'},
    {'value': 'arrange', 'label': 'アレンジ', 'icon': 'fas fa-sliders-h'},
    {'value': 'otomad', 'label': '音MAD', 'icon': 'fas fa-cut'},
    {'value': 'medley', 'label': 'メドレー', 'icon': 'fas fa-stream'},
    {'value': 'omnibus', 'label': '総集編', 'icon': 'fas fa-archive'},
    {'value': 'notice', 'label': '予告', 'icon': 'fas fa-bell'},
    {'value': 'offv', 'label': 'オフボ', 'icon': 'fas fa-microphone-slash'},
    {'value': 'cover', 'label': 'カバー', 'icon': 'fas fa-microphone'},
    {'value': 'meme', 'label': 'ネタ動画', 'icon': 'far fa-laugh-squint'},
]

# cookieとキャッシュの保存期間
# SHORT_TERM: 30分（一般ページのキャッシュ用）
# LONG_TERM: 365日（静的ファイルのキャッシュ、ユーザー設定のcookie用）
SHORT_TERM_COOKIE_AGE = 30 * 60
LONG_TERM_COOKIE_AGE = 365 * 24 * 60 * 60

# 検索画面のフォームを切り替えるラジオボタンの表示（設定画面のフォームボタン）
FORM_BUTTON_CHOICES = {"icon", "icon_text"}
FORM_BUTTON_DEFAULT = "icon_text"

# サイト全体のフォント（設定画面のフォント、#584）。imitateは源全ゴシック、k8x12sはドットフォント
FONT_CHOICES = {"imitate", "k8x12s"}
FONT_DEFAULT = "imitate"

# 曲の並び替えの選択肢（曲の検索画面・作者ページ、#606）
# 曲の検索画面では、YouTube関連の並び替え(YOUTUBE_SORTS)はラベルにYouTubeのアイコンを付ける
SORT_CHOICES = [
    {'value': 'id', 'icon': 'fa fa-plus', 'label': '登録日/早い順'},
    {'value': '-id', 'icon': 'fa fa-plus', 'label': '登録日/遅い順'},
    {'value': 'post_time', 'icon': 'fas fa-file-signature', 'label': '更新日/早い順'},
    {'value': '-post_time', 'icon': 'fas fa-file-signature', 'label': '更新日/遅い順'},
    {'value': 'upload_time', 'icon': 'far fa-calendar-alt', 'label': '投稿日/早い順'},
    {'value': '-upload_time', 'icon': 'far fa-calendar-alt', 'label': '投稿日/遅い順'},
    {'value': 'view', 'icon': 'fas fa-play', 'label': '再生回数/少ない順'},
    {'value': '-view', 'icon': 'fas fa-play', 'label': '再生回数/多い順'},
    {'value': 'like', 'icon': 'far fa-thumbs-up', 'label': '高評価数/少ない順'},
    {'value': '-like', 'icon': 'far fa-thumbs-up', 'label': '高評価数/多い順'},
    {'value': 'imitate_count', 'icon': 'fas fa-sitemap imitate', 'label': '模倣元の数/少ない順'},
    {'value': '-imitate_count', 'icon': 'fas fa-sitemap imitate', 'label': '模倣元の数/多い順'},
    {'value': 'imitated_count', 'icon': 'fas fa-sitemap', 'label': '模倣曲の数/少ない順'},
    {'value': '-imitated_count', 'icon': 'fas fa-sitemap', 'label': '模倣曲の数/多い順'},
    {'value': 'random', 'icon': 'fas fa-random', 'label': 'ランダム'},
]

HISTORIES_PER_PAGE = 50

# スマホ幅の曲カードに並べるフラグのアイコンの上限。超えるときは、残りを三点リーダーのアイコンにまとめて、三点リーダーも含めてこの数に収める（#1229）
SONG_CARD_SP_MAX_FLAG_ICONS = 2

# 全てあなたの所為です。の作者ID
SUBEANA_AUTHOR_ID = 1

# 編集の変更履歴（History.changes）の見出しの行
EDIT_CHANGES_HEADER = ["種類", "編集前", "編集後"]

RECOMEND_ARTICLES = [
    {
        "url_name": "article:default_article",
        "args": ["lilyriku"],
        "title": "すべかしオリキャラ「リリ」と「リク」のご紹介",
    },
    {
        "url_name": "article:default_article",
        "args": ["discord"],
        "title": "すべかしDiscordサーバーのご案内",
    },
    {
        "url": "https://izumin2000.github.io/anniversary6/",
        "title": "6周年記念グラフィックアート",
    },
]
