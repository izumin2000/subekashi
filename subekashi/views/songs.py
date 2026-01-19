from django.shortcuts import render
from subekashi.constants.constants import ALL_MEDIAS


QUERY_OR_COOKIE_FORMS = [
    ("isdetail", "isdetail", "False"),
    ("songrange", "issubeana", "subeana"),
    ("jokerange", "isjoke", "off"),
    ("sort", "sort", "-post_time"),
]

FILER_FORMS = ["issubeana", "isjoke", "islack", "isdraft", "isoriginal", "isinst", "isdeleted"]
DISPLAY_MEDIA_INDEX = 5

def songs(request) :
    dataD = {
        "metatitle" : "一覧と検索",
        "ALL_MEDIAS": ALL_MEDIAS[:-1],     # 最後の許可されていないURLのドメイン情報は不要
        "display_media_index": DISPLAY_MEDIA_INDEX
    }

    GET = request.GET
    COOKIES = request.COOKIES
    cookies_to_set = {}

    for form, flag, defalut in QUERY_OR_COOKIE_FORMS:
        if GET.get(flag):
            dataD[form] = GET[flag]
            cookies_to_set[f"search_{form}"] = GET[flag]
        else:
            dataD[form] = COOKIES.get(f"search_{form}", defalut)

    for filter in FILER_FORMS:
        dataD[filter] = bool(GET.get(filter))

    response = render(request, "subekashi/songs.html", dataD)

    for cookie_name, cookie_value in cookies_to_set.items():
        response.set_cookie(cookie_name, cookie_value, max_age=31104000, path='/')

    return response