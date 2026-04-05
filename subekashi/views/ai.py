from django.shortcuts import render
from subekashi.models import Ai
from subekashi.lib.discord import send_discord
from subekashi.constants.constants import CONST_ERROR
from config.local_settings import ERROR_DISCORD_URL


def ai(request):
    dataD = {
        "metatitle": "歌詞生成",
    }

    try:
        from subekashi.constants.dynamic.ai import GENEINFO
    except Exception:
        send_discord(ERROR_DISCORD_URL, CONST_ERROR)
        GENEINFO = {}
    dataD.update(GENEINFO)

    dataD["bestInsL"] = Ai.get_high_scored_model()
    return render(request, "subekashi/ai.html", dataD)
