from django.shortcuts import render
from django.views.decorators.cache import never_cache
from article.models import Article
import markdown


@never_cache
def default_article(request, id):
    try:
        article = Article.objects.get(pk = id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    # 記事本文がマークダウンかどうかによってMD -> HTMLにする
    text = markdown.markdown(article.text) if article.is_md else article.text
    
    dataD = {
        "article": article,
        "text": text
    }
    return render(request, 'article/default_article.html', dataD)