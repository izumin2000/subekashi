from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from subekashi.models import Song, Ai, Ad
from subekashi.lib.query_filters import filter_by_lack
from subekashi.constants.constants import RECOMEND_ARTICLES, LONG_TERM_COOKIE_AGE
from subekashi.views.songs import get_search_form_context
from subekashi.views.setting import ALLOWED_SETTING_VALUES
from article.models import Article
import random


@method_decorator(never_cache, name='dispatch')
class TopView(View):
    def get(self, request):
        recomend_articles = [
            {
                "url": article["url"] if "url" in article else reverse(article["url_name"], args=article["args"]),
                "title": article["title"],
                "external": "url" in article,
            }
            for article in RECOMEND_ARTICLES
        ]
        
        context = {
            "metatitle": "トップ",
            "RECOMEND_ARTICLES": recomend_articles
        }

        # 初心者向け案内の表示設定（×ボタンで閉じるとtop.jsでoffにする、#1236）
        is_shown_guide = request.COOKIES.get("is_shown_guide", "on") != "off"
        context["is_shown_guide"] = is_shown_guide
        if is_shown_guide:
            context["guide_cookie_age"] = LONG_TERM_COOKIE_AGE

        article_qs = Article.get_top_news_articles()

        news_htmls = ""
        for article in article_qs:
            should_link = article.handle_as_news or article.tag != "news"
            if should_link:
                article_url = reverse('article:default_article', args=[article.article_id])
                news_html = f"<a href='{article_url}'>{article.title_without_links}</a>"
            else:
                news_html = article.title
            news_htmls += f"<span>{news_html}</span>"
        context["news_htmls"] = news_htmls

        # 検索の表示設定（all: 検索画面と同じフォーム、on: キーワードのみ、off: 非表示）
        is_shown_search = request.COOKIES.get("is_shown_search", "on")
        # cookieが不正な値の場合はデフォルトのキーワードのみとする
        if is_shown_search not in ALLOWED_SETTING_VALUES["is_shown_search"]:
            is_shown_search = "on"
        context["is_shown_search"] = is_shown_search
        if is_shown_search == "all":
            # トップ画面では検索の選択肢のcookieを保存しないため、URLクエリは渡さない
            search_form_context, _ = get_search_form_context(request, {})
            context.update(search_form_context)

        songrange = request.COOKIES.get("songrange", "subeana")
        jokerange = request.COOKIES.get("jokerange", "off")

        songInsL = Song.get_for_range(songrange, jokerange)

        # 新着の表示設定
        new_count = int(request.COOKIES.get("is_shown_new", "5"))
        if new_count > 0:
            context["songInsL"] = songInsL.order_by('-id')[:new_count]

        # 投稿予定の表示設定（YouTubeの投稿日が未来の曲を、投稿日の早い順に表示する、#376）
        upcoming_count = request.COOKIES.get("is_shown_upcoming", "5")
        # cookieが不正な値の場合はデフォルトの5曲とする
        if upcoming_count not in ALLOWED_SETTING_VALUES["is_shown_upcoming"]:
            upcoming_count = "5"
        upcoming_count = int(upcoming_count)
        if upcoming_count > 0:
            context["upcomingInsL"] = songInsL.filter(upload_time__gt=timezone.now()).order_by('upload_time', 'id')[:upcoming_count]

        # 未完成の表示設定
        lack_count = int(request.COOKIES.get("is_shown_lack", "5"))
        if lack_count > 0:
            lackInsL = list(songInsL.filter(filter_by_lack()))
            if lackInsL:
                lackInsL = random.sample(lackInsL, min(lack_count, len(lackInsL)))
                context["lackInsL"] = lackInsL

        # 作成された歌詞の表示設定
        is_ai_shown = request.COOKIES.get("is_shown_ai", "on") == "on"
        if is_ai_shown:
            aiInsL = list(Ai.get_top_scored())[::-1]
            if aiInsL:
                context["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]

        # 宣伝の表示設定
        is_shown_ad = request.COOKIES.get("is_shown_ad", "on") == "on"
        context["is_shown_ad"] = is_shown_ad
        if is_shown_ad:
            adInsL = list(Ad.get_active())
            if adInsL:
                adInsL = random.sample(adInsL, min(len(adInsL), 10))
                adInsL = [adIns for adIns in adInsL for _ in range(adIns.dup)]
                adIns = random.choice(adInsL) if adInsL else []
                context["adIns"] = adIns

        return render(request, 'subekashi/top.html', context)
