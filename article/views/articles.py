from django.shortcuts import render
from django.db.models import Q
from article.models import Article

def articles(request):
    tag_filter = request.GET.get("tag", "")
    keyword = request.GET.get("keyword", "")

    articles = Article.objects.filter(is_open=True)

    if tag_filter and tag_filter != "all":
        articles = articles.filter(tag=tag_filter)

    if keyword:
        articles = articles.filter(
            Q(title__icontains=keyword) |
            Q(author__icontains=keyword) |
            Q(text__icontains=keyword)
        )

    articles = articles.order_by("-post_time")

    response = render(request, 'article/articles.html', {
        "articles": articles,
        "selected_tag": tag_filter,
        "keyword": keyword,
        "tags": Article.TAGS
    })

    return response