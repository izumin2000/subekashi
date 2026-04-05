from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from django.views import View
from article.models import Article


class ArticlesView(View):
    def get(self, request):
        tag_filter = request.GET.get("tag", "")
        keyword = request.GET.get("keyword", "")

        articles_qs = Article.objects.filter(is_open=True, post_time__lte=timezone.now())

        if tag_filter and tag_filter != "all":
            articles_qs = articles_qs.filter(tag=tag_filter)

        if keyword:
            articles_qs = articles_qs.filter(
                Q(title__icontains=keyword) |
                Q(author__icontains=keyword) |
                Q(text__icontains=keyword)
            )

        articles_qs = articles_qs.order_by("-post_time")

        context = {
            "metatitle": "記事一覧",
            "articles": articles_qs,
            "selected_tag": tag_filter,
            "keyword": keyword,
            "tags": Article.TAGS
        }
        return render(request, 'article/articles.html', context)
