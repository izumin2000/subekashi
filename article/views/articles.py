from django.shortcuts import render
from article.models import Article

def articles(request):
    dataD = {"articles": Article.objects.filter(is_open = True).order_by("-post_time")}
    return render(request, 'article/articles.html', dataD)