from django.shortcuts import render
from article.models import Article

def articles(request):
    dataD = {"articles": Article.objects.filter(is_open = True)}
    return render(request, 'article/articles.html', dataD)