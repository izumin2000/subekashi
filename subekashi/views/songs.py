from django.shortcuts import render
from subekashi.constants.constants import ALL_MEDIAS


QUERY_OR_COOKIE_FORMS = [
    ("isdetail", "isdetail", "False"),
    ("songrange", "issubeana", "subeana"),
    ("jokerange", "isjoke", "off"),
    ("sort", "sort", "-post_time"),
]

FILER_FORMS = ["issubeana", "isjoke", "islack", "isdraft", "isoriginal", "isinst", "isdeleted"]
DISPLAY_MEDIA_INDEX = 6

def songs(request) :
    dataD = {
        "metatitle" : "一覧と検索",
        "ALL_MEDIAS": ALL_MEDIAS[:-1],     # 最後の許可されていないURLのドメイン情報は不要
        "hidden_media_index": len(ALL_MEDIAS) - DISPLAY_MEDIA_INDEX - 1
    }
    
    GET = request.GET
    COOKIES = request.COOKIES
    for form, flag, defalut in QUERY_OR_COOKIE_FORMS:
        dataD[form] = GET[flag] if GET.get(flag) else COOKIES.get(f"search_{form}", defalut)
    
    for filter in FILER_FORMS:
        dataD[filter] = bool(GET.get(filter))
    
    return render(request, "subekashi/songs.html", dataD)