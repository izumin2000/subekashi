from django.shortcuts import render
from subekashi.constants.constants import ALL_MEDIAS, LONG_TERM_COOKIE_AGE


# Cookieに保存するフォームの設定
COOKIE_FORMS = {
    'isdetail': {
        'query_name': 'isdetail',
        'values': {'True', 'False'},
        'default': 'False'
    },
    'songrange': {
        'query_name': 'issubeana',
        'values': {'all', 'subeana', 'xx'},
        'default': 'subeana'
    },
    'jokerange': {
        'query_name': 'isjoke',
        'values': {'on', 'off', 'only'},
        'default': 'off'
    },
    'sort': {
        'query_name': 'sort',
        'values': {'id', '-id', 'post_time', '-post_time', 'upload_time', '-upload_time', '-view', 'view', '-like', 'like', 'random'},
        'default': '-post_time'
    }
}

# チェックボックス
BOOL_FORMS = ["issubeana", "isjoke", "islack", "isdraft", "isoriginal", "isinst", "isdeleted"]

# 折りたたまれていないメディアタイプ
DISPLAY_MEDIA_INDEX = 5

def songs(request):
    dataD = {
        "metatitle" : "一覧と検索",
        "ALL_MEDIAS": ALL_MEDIAS[:-1],     # 最後の許可されていないURLのドメイン情報は不要
        "display_media_index": DISPLAY_MEDIA_INDEX
    }

    # POSTリクエストの場合はGET、それ以外はGET
    REQUEST_DATA = request.POST if request.method == 'POST' else request.GET
    COOKIES = request.COOKIES
    cookies_to_set = {}

    for form_name, form_config in COOKIE_FORMS.items():
        query_name = form_config['query_name']
        default_value = form_config['default']
        allowed_values = form_config['values']

        if REQUEST_DATA.get(query_name):
            value = REQUEST_DATA[query_name]
            # 許可された値に対してバリデーションを実行
            if value not in allowed_values:
                dataD[form_name] = default_value  # 不正な値の場合はデフォルト値を使用
            else:       # URLクエリやユーザーのCOOKIE_FORMSの変更の場合はcookieに値を保存するcookies_to_setに書き込む
                dataD[form_name] = value
                cookies_to_set[f"search_{form_name}"] = value
        else:
            cookie_value = COOKIES.get(f"search_{form_name}", default_value)
            dataD[form_name] = cookie_value

    # チェックボックスのURLクエリ対応
    for filter in BOOL_FORMS:
        dataD[filter] = bool(REQUEST_DATA.get(filter))

    response = render(request, "subekashi/songs.html", dataD)

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