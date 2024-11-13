from django.shortcuts import render
from config.settings import *
from subekashi.models import *
from subekashi.constants.constants import *
from subekashi.lib.filter import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from bs4 import BeautifulSoup
import random
import markdown

INPUT_TEXTS = ["title", "channel", "lyrics", "url"]

def top(request):
    dataD = {
        "metatitle" : "トップ",
    }
    
    news_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/news.md')
    if os.path.exists(news_path):
        file = open(news_path, 'r', encoding='utf-8')
        news_md = file.read()
        file.close()
        news_html = markdown.markdown(news_md)
        news_soup = BeautifulSoup(news_html, 'html.parser')
    
        for a in news_soup.find_all('a'):
            a['target'] = '_blank'

        news = str(news_soup)
        dataD["news"] = news
    else :
        dataD["news"] = CONST_ERROR
    
    songrange = request.COOKIES.get("songrange", "subeana")
    jokerange = request.COOKIES.get("jokerange", "off")
    
    if songrange == "all" :
        songInsL = Song.objects.all()
    elif songrange == "subeana" :
        songInsL = Song.objects.filter(issubeana = True)
    elif songrange == "xx" :
        songInsL = Song.objects.filter(issubeana = False)
    if jokerange == "off" :
        songInsL = songInsL.filter(isjoke = False)
        
    dataD["songInsL"] = list(songInsL)[:-7:-1]
    lackInsL = list(songInsL.filter(islack))
    if lackInsL :
        lackInsL = random.sample(lackInsL, min(6, len(lackInsL)))
        dataD["lackInsL"] = lackInsL
    aiInsL = Ai.objects.filter(score = 5)[::-1]
    
    if aiInsL :
        dataD["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]
        
    isAdDisplay = request.COOKIES.get("adrange", "off") == "on"
    dataD["isAdDisplay"] = isAdDisplay
    adInsL = Ad.objects.filter(status = "pass") if isAdDisplay else ""
    if adInsL :
        adInsL = random.sample(list(adInsL), min(len(adInsL), 10))
        adInsL = [adIns for adIns in adInsL for _ in range(adIns.dup)]
        adIns = random.choice(adInsL) if adInsL else []
        dataD["adIns"] = adIns
    
    return render(request, 'subekashi/top.html', dataD)