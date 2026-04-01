from django.shortcuts import render
from django.views.decorators.cache import never_cache
from subekashi.models import Song, Ai, Ad
from subekashi.lib.query_filters import filter_by_lack
from subekashi.lib.song_service import get_top_news_articles
import random


@never_cache
def top(request):
    dataD = {
        "metatitle": "トップ",
    }

    article_qs = get_top_news_articles()

    news_htmls = ""
    for article in article_qs:
        is_news = article.tag == "news"
        news_html = article.title if is_news else f"<a href='/articles/{article.article_id}'>{article.title}</a>"
        news_htmls += f"<span>{news_html}</span>"
    dataD["news_htmls"] = news_htmls

    songrange = request.COOKIES.get("songrange", "subeana")
    jokerange = request.COOKIES.get("jokerange", "off")

    songInsL = Song.get_for_range(songrange, jokerange)

    # 新着の表示設定
    new_count = int(request.COOKIES.get("is_shown_new", "5"))
    if new_count > 0:
        dataD["songInsL"] = list(songInsL)[:-(new_count + 1):-1]

    # 未完成の表示設定
    lack_count = int(request.COOKIES.get("is_shown_lack", "5"))
    if lack_count > 0:
        lackInsL = list(songInsL.filter(filter_by_lack()))
        if lackInsL:
            lackInsL = random.sample(lackInsL, min(lack_count, len(lackInsL)))
            dataD["lackInsL"] = lackInsL

    # 生成された歌詞の表示設定
    is_ai_shown = request.COOKIES.get("is_shown_ai", "on") == "on"
    if is_ai_shown:
        aiInsL = list(Ai.get_top_scored())[::-1]
        if aiInsL:
            dataD["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]

    # 宣伝の表示設定
    is_shown_ad = request.COOKIES.get("is_shown_ad", "on") == "on"
    dataD["is_shown_ad"] = is_shown_ad
    if is_shown_ad:
        adInsL = list(Ad.get_active())
        if adInsL:
            adInsL = random.sample(adInsL, min(len(adInsL), 10))
            adInsL = [adIns for adIns in adInsL for _ in range(adIns.dup)]
            adIns = random.choice(adInsL) if adInsL else []
            dataD["adIns"] = adIns

    return render(request, 'subekashi/top.html', dataD)
