from django.shortcuts import render
from subekashi.constants.constants import   URLS


QUERY_OR_COOKIE_FORMS = [
    ("isdetail", "isdetail", "False"),
    ("songrange", "issubeana", "subeana"),
    ("jokerange", "isjoke", "off"),
    ("sort", "sort", "-post_time"),
]

FILER_FORMS = ["issubeana", "isjoke", "islack", "isdraft", "isoriginal", "isinst", "isdeleted"]

def songs(request) :
    dataD = {
        "metatitle" : "一覧と検索",
    }
    
    GET = request.GET
    COOKIES = request.COOKIES
    for form, flag, defalut in QUERY_OR_COOKIE_FORMS:
        dataD[form] = GET[flag] if GET.get(flag) else COOKIES.get(f"search_{form}", defalut)
    
    for filter in FILER_FORMS:
        dataD[filter] = bool(GET.get(filter))
    
    # メディアリスト
    media_checks = []
    # URLSに未登録時の挙動を追加する
    medias = {
        **URLS,
        "nourl":(["^$"],"","URL未登録")
    }
    for name,tuple in medias.items():
        url,icon,display_name = tuple
        media_checks.append(f"""<div class="checkbox-col"><input type="checkbox" value="media-{name}" id="media-{name}" name="media-{name}" checked><label for="media-{name}">{icon}{display_name}</label></div>""")
    dataD["medias"] = "\n".join(media_checks)

    return render(request, "subekashi/songs.html", dataD)