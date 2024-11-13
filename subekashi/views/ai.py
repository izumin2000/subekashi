from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.discord import *


def ai(request) :
    dataD = {
        "metatitle" : "歌詞生成",
    }
    
    try:
        from subekashi.constants.dynamic.ai import GENEINFO
    except :
        sendDiscord(ERROR_DISCORD_URL, CONST_ERROR)
        GENEINFO = {}
    dataD.update(GENEINFO)
    
    if request.method == "POST" :
        aiIns = Ai.objects.filter(genetype = "model", score = 0)
        if not aiIns.exists() :
            sendDiscord(ERROR_DISCORD_URL, "aiInsのデータがありません。")
            aiIns = Ai.objects.filter(genetype = "model")
        dataD["aiInsL"] = aiIns.order_by('?')[:25]
        return render(request, "subekashi/ai_result.html", dataD)
    
    dataD["bestInsL"] = Ai.objects.filter(genetype = "model", score = 5).order_by('?')[:300]
    return render(request, "subekashi/ai.html", dataD)