import json
import os
from django.shortcuts import render
from config.settings import BASE_DIR
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.discord import *
from subekashi.constants.constants import CONST_ERROR

AI_JSON_PATH = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/ai.json')


def ai(request) :
    dataD = {
        "metatitle" : "歌詞生成",
    }
    
    try:
        with open(AI_JSON_PATH, "r", encoding="utf-8") as f:
            GENEINFO = json.load(f)
    except:
        send_discord(ERROR_DISCORD_URL, CONST_ERROR)
        GENEINFO = {}
    dataD.update(GENEINFO)
    
    dataD["bestInsL"] = Ai.objects.filter(genetype = "model", score = 5).order_by('?')[:300]
    return render(request, "subekashi/ai.html", dataD)