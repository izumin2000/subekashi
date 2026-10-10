import os
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from config.settings import *


ROBOTS_PATH = os.path.join(BASE_DIR, "subekashi", "static", "subekashi", "robots.txt")


def robots(request) :
    with open(ROBOTS_PATH, encoding="utf-8") as f:
        return HttpResponse(f.read(), content_type="text/plain; charset=utf-8")


# TODO subekashi:***へ
def sitemap(request) :
    return redirect(f"{ROOT_URL}/static/subekashi/sitemap.xml")


def favicon(request) :
    return redirect(f"{ROOT_URL}/static/subekashi/image/icon.ico")


def trafficAdvice(request) :
    return JsonResponse({}, safe=False)