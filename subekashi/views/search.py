from django.shortcuts import render

QUERY_OR_COOKIE_FORMS = [
    ("songrange", "issubeana", "subeana"),
    ("jokerange", "isjoke", "off"),
    ("sort", "sort", "post_time"),
    ("isauto", "isauto", True),
]
# TODO constantsに移動
FILER_FORMS = ["issubeana", "isjoke", "isdraft", "isoriginal", "isinst"]

def search(request) :
    dataD = {
        "metatitle" : "一覧と検索",
    }
    
    GET = request.GET
    COOKIES = request.COOKIES
    for form, flag, defalut in QUERY_OR_COOKIE_FORMS:
        dataD[form] = GET[flag] if GET.get(flag) else COOKIES.get(f"search_{form}", defalut)
    
    for filter in FILER_FORMS:
        dataD[filter] = bool(GET.get(filter))

    return render(request, "subekashi/search.html", dataD)