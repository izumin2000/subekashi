from django.shortcuts import render
from django.views import View
from article.models import Article
import markdown


class DefaultArticleView(View):
    def get(self, request, id):
        try:
            article = Article.objects.get(pk=id)
        except Article.DoesNotExist:
            return render(request, 'subekashi/404.html', status=404)

        if not article.is_open:
            return render(request, 'subekashi/404.html', status=404)

        # 記事本文がマークダウンかどうかによってMD -> HTMLにする
        text = markdown.markdown(article.text) if article.is_md else article.text

        context = {
            "metatitle": article.title,
            "article": article,
            "text": text
        }
        return render(request, 'article/default_article.html', context)
