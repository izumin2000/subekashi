from django.shortcuts import redirect
from django.http import JsonResponse
from config.settings import *



def robots(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/robots.txt")


def sitemap(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/sitemap.xml")


def favicon(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/image/icon.ico")


def trafficAdvice(request) :
    return JsonResponse({}, safe=False)