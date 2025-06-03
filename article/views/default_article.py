from django.shortcuts import render
from article.models import Article

def default_article(request, id):
    try:
        article = Article.objects.get(pk = id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {"article": article}
    return render(request, 'article/default_article.html', dataD)