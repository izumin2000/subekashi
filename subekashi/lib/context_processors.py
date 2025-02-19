from django.urls import resolve
from subekashi.constants.constants import *

def context_processors(request):
    context = {
        'aside_pages': ASIDE_PAGES,
    }

    # ページ名を取得
    view_name = resolve(request.path_info).view_name
    for page in PAGES:
        if page["url"] == f"subekashi:{view_name}":
            context['page_name'] = page["name"]
            break

    return context