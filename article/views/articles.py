from django.shortcuts import render
from django.views.decorators.cache import never_cache
from article.models import Article

@never_cache
def articles(request):
    dataD = {"articles": Article.objects.filter(is_open = True).order_by("-post_time")}
    return render(request, 'article/articles.html', dataD)