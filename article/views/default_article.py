from django.shortcuts import render
from django.views import View
from article.models import Article
import markdown
import re


# 記事本文は管理者のみが編集できる信頼済みのHTMLのため、本文中の<script>にもCSPのnonceを付与して実行を許可する
def add_csp_nonce(text, nonce):
    return re.sub(r'<script(?=[\s>])', f'<script nonce="{nonce}"', text, flags=re.IGNORECASE)


class DefaultArticleView(View):
    def get(self, request, id):
        try:
            article = Article.objects.get(pk=id)
        except Article.DoesNotExist:
            return render(request, 'subekashi/404.html', status=404)

        if not article.is_open:
            return render(request, 'subekashi/404.html', status=404)

        # 記事本文がマークダウンかどうかによってMD -> HTMLにする
        text = markdown.markdown(article.text, extensions=['tables']) if article.is_md else article.text
        if text:
            text = add_csp_nonce(text, getattr(request, "csp_nonce", ""))

        context = {
            "metatitle": article.title,
            "article": article,
            "text": text
        }
        return render(request, 'article/default_article.html', context)
