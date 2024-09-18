from django.shortcuts import render
from config.settings import *
from subekashi.lib.discord import *
import traceback


def handle_404_error(request, exception=None):
    dataD = {
        "metatitle" : "全てエラーの所為です。",
    }
    return render(request, 'subekashi/404.html', dataD, status=404)
    

def handle_500_error(request):
    dataD = {
        "metatitle" : "全て五百の所為です。",
    }
    error_msg = traceback.format_exc()
    sendDiscord(ERROR_DISCORD_URL, error_msg)
    return render(request, 'subekashi/500.html', dataD, status=500)