from django.shortcuts import render
from django.db.models import Q
from config.settings import *
from subekashi.models import *
from article.models import Article
from subekashi.constants.constants import *
from subekashi.lib.filter import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
import random

INPUT_TEXTS = ["title", "channel", "lyrics", "url"]


def top(request):
    dataD = {
        "metatitle" : "トップ",
    }
    
    article_qs = Article.objects.filter(
        is_open=True
    ).filter(
        Q(tag="news") | Q(tag="release")
    ).order_by("-post_time")[:3]
    
    news_htmls = ""
    for article in article_qs:
        is_news = article.tag == "news"
        news_html = article.title if is_news else f"<a href='/articles/{article.article_id}'>{article.title}</a>"
        news_htmls += f"<span>{news_html}</span>"
    dataD["news_htmls"] = news_htmls
    
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
    lackInsL = list(songInsL.filter(filter_by_lack))
    if lackInsL :
        lackInsL = random.sample(lackInsL, min(6, len(lackInsL)))
        dataD["lackInsL"] = lackInsL
    aiInsL = Ai.objects.filter(score = 5)[::-1]
    
    if aiInsL :
        dataD["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]
        
    isAdDisplay = request.COOKIES.get("is-shown-ad", "off") == "on"
    dataD["isAdDisplay"] = isAdDisplay
    adInsL = Ad.objects.filter(status = "pass") if isAdDisplay else ""
    if adInsL :
        adInsL = random.sample(list(adInsL), min(len(adInsL), 10))
        adInsL = [adIns for adIns in adInsL for _ in range(adIns.dup)]
        adIns = random.choice(adInsL) if adInsL else []
        dataD["adIns"] = adIns
    
    return render(request, 'subekashi/top.html', dataD)