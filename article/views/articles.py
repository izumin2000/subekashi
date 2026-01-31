from django.shortcuts import render
from django.db.models import Q
from django.utils import timezone
from article.models import Article

def articles(request):
    tag_filter = request.GET.get("tag", "")
    keyword = request.GET.get("keyword", "")

    articles = Article.objects.filter(is_open=True, post_time__lte=timezone.now())

    if tag_filter and tag_filter != "all":
        articles = articles.filter(tag=tag_filter)

    if keyword:
        articles = articles.filter(
            Q(title__icontains=keyword) |
            Q(author__icontains=keyword) |
            Q(text__icontains=keyword)
        )

    articles = articles.order_by("-post_time")

    return render(request, 'article/articles.html', {
        "metatitle": "記事一覧",
        "articles": articles,
        "selected_tag": tag_filter,
        "keyword": keyword,
        "tags": Article.TAGS
    })