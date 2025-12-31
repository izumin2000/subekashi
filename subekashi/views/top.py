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

    # 新着の表示設定
    new_count = int(request.COOKIES.get("is_shown_new", "5"))
    if new_count > 0:
        dataD["songInsL"] = list(songInsL)[:-(new_count + 1):-1]

    # 未完成の表示設定
    lack_count = int(request.COOKIES.get("is_shown_lack", "5"))
    if lack_count > 0:
        lackInsL = list(songInsL.filter(filter_by_lack))
        if lackInsL:
            lackInsL = random.sample(lackInsL, min(lack_count, len(lackInsL)))
            dataD["lackInsL"] = lackInsL

    # 生成された歌詞の表示設定
    is_ai_shown = request.COOKIES.get("is-show-ai", "on") == "on"
    if is_ai_shown:
        aiInsL = Ai.objects.filter(score = 5)[::-1]
        if aiInsL:
            dataD["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]

    # 宣伝の表示設定
    is_shown_ad = request.COOKIES.get("is_shown_ad", "on") == "on"
    dataD["is_shown_ad"] = is_shown_ad
    if is_shown_ad:
        adInsL = Ad.objects.filter(status = "pass")
        if adInsL:
            adInsL = random.sample(list(adInsL), min(len(adInsL), 10))
            adInsL = [adIns for adIns in adInsL for _ in range(adIns.dup)]
            adIns = random.choice(adInsL) if adInsL else []
            dataD["adIns"] = adIns
    
    return render(request, 'subekashi/top.html', dataD)