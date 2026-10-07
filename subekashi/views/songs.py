from django.shortcuts import render
from django.views import View
from subekashi.constants.constants import ALL_MEDIAS, LONG_TERM_COOKIE_AGE
from subekashi.lib.query_utils import YOUTUBE_FILTERS, YOUTUBE_SORTS


# 並び替えの選択肢（YouTube関連の並び替え(YOUTUBE_SORTS)はラベルにYouTubeのアイコンを付ける）
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

# Cookieに保存するフォームの設定
COOKIE_FORMS = {
    'songrange': {
        'values': {'all', 'subeana', 'xx'},
        'default': 'all'
    },
    'jokerange': {
        'values': {'on', 'off', 'only'},
        'default': 'on'
    },
    'sort': {
        'values': {choice['value'] for choice in SORT_CHOICES},
        'default': '-post_time'
    }
}

# 真偽値のフィルタ（True・False・フィルタなしの3値）
BOOL_FORMS = ["is_subeana", "is_joke", "is_lack", "is_draft", "is_original", "is_inst", "is_deleted", "is_questionable", "is_special", "is_collab"]

# ラジオボタンで切り替えるフォームと、そのフォームに含まれるURLクエリ
# URLクエリが指定されている場合は該当するフォームを初期表示する
# 画面にフォームがあるクエリのみ（imitated・guesser・title_exact等のAPI専用のクエリは画面で扱わない）
SEARCH_FORM_QUERIES = {
    'keyword': ['keyword'],
    'sort': ['sort'],
    'lyrics': ['lyrics'],
    'youtube': YOUTUBE_FILTERS,
    'title': ['title'],
    'author': ['author'],
    'url': ['url', 'mediatypes'],
    'imitate': ['imitate'],
    'subeana': ['songrange', 'is_subeana'],
    'joke': ['jokerange', 'is_joke'],
    'original': ['is_original'],
    'inst': ['is_inst'],
    'questionable': ['is_questionable'],
    'special': ['is_special'],
    'collab': ['is_collab'],
    'deleted': ['is_deleted'],
    'lack': ['is_lack'],
    'draft': ['is_draft'],
}
DEFAULT_SEARCH_FORM = 'keyword'

# 折りたたまれていないメディアタイプ
DISPLAY_MEDIA_INDEX = 6


class SongsView(View):
    def get(self, request):
        return self._handle(request)

    def post(self, request):
        return self._handle(request)

    def _handle(self, request):
        context = {
            "metatitle": "一覧と検索",
            "ALL_MEDIAS": ALL_MEDIAS[:-1],     # 最後の許可されていないURLのドメイン情報は不要
            "display_media_index": DISPLAY_MEDIA_INDEX,
            "SORT_CHOICES": SORT_CHOICES,
            # 自動で適用されるフィルタの案内に使用する（songs.js）
            "youtube_queries": {"filters": YOUTUBE_FILTERS, "sorts": YOUTUBE_SORTS},
        }

        # POSTリクエストの場合はPOST、それ以外はGET
        REQUEST_DATA = request.POST if request.method == 'POST' else request.GET
        COOKIES = request.COOKIES
        cookies_to_set = {}

        # is_saved_selectの設定を確認
        is_saved_select = COOKIES.get('is_saved_select', 'on')

        for form_name, form_config in COOKIE_FORMS.items():
            default_value = form_config['default']
            allowed_values = form_config['values']

            if REQUEST_DATA.get(form_name):
                value = REQUEST_DATA[form_name]
                # 許可された値に対してバリデーションを実行
                if value not in allowed_values:
                    context[form_name] = default_value  # 不正な値の場合はデフォルト値を使用
                else:       # URLクエリやユーザーのCOOKIE_FORMSの変更の場合はcookieに値を保存するcookies_to_setに書き込む
                    context[form_name] = value
                    # is_saved_selectがonの場合のみcookieに保存
                    if is_saved_select == 'on':
                        cookies_to_set[f"search_{form_name}"] = value
            else:
                # is_saved_selectがoffの場合はcookieを無視してデフォルト値を使用
                if is_saved_select == 'off':
                    context[form_name] = default_value
                else:
                    cookie_value = COOKIES.get(f"search_{form_name}", default_value)
                    # cookieが不正な値の場合はデフォルト値を使用
                    context[form_name] = cookie_value if cookie_value in allowed_values else default_value

        # 真偽値のフィルタのURLクエリ対応
        for filter in BOOL_FORMS:
            raw = REQUEST_DATA.get(filter)
            if raw is None:
                continue
            value_lower = raw.lower()
            # is_subeana/is_joke は曲詳細ページのタグリンク等からの一時的な絞り込み用パラメータのため、
            # その表示にのみ反映し、検索の保存設定(cookie)は上書きしない
            if filter == "is_subeana":
                songrange_value = "subeana" if value_lower in ["true", "1"] else "xx"
                context["songrange"] = songrange_value
            elif filter == "is_joke":
                if value_lower in ["true", "1", "only"]:
                    jokerange_value = "only"
                elif value_lower in ["all", "on"]:
                    jokerange_value = "on"
                else:
                    jokerange_value = "off"
                context["jokerange"] = jokerange_value
            elif value_lower in ["true", "1"]:
                context[filter] = "True"
            elif value_lower in ["false", "0"]:
                context[filter] = "False"

        # メディアのチェックボックスのURLクエリ対応（カンマ区切り）
        context["mediatypes"] = REQUEST_DATA.get("mediatypes", "").split(",")

        context["search_form"] = next(
            (form for form, queries in SEARCH_FORM_QUERIES.items() if any(REQUEST_DATA.get(query) for query in queries)),
            DEFAULT_SEARCH_FORM
        )

        response = render(request, "subekashi/songs.html", context)

        # 実際にCOOKIEに保存
        for cookie_name, cookie_value in cookies_to_set.items():
            response.set_cookie(
                cookie_name,
                cookie_value,
                max_age=LONG_TERM_COOKIE_AGE,
                path='/',
                samesite='Lax'
            )

        return response
