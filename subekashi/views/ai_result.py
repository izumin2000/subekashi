from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.discord import *


def ai_result(request) :
    dataD = {
        "metatitle" : "歌詞の生成結果",
    }
    
    aiIns = Ai.objects.filter(genetype = "model", score = 0)
    if not aiIns.exists() :
        send_discord(ERROR_DISCORD_URL, "aiInsのデータがありません。")
        aiIns = Ai.objects.filter(genetype = "model")
    dataD["aiInsL"] = aiIns.order_by('?')[:25]
    return render(request, "subekashi/ai_result.html", dataD)
