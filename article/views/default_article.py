from django.shortcuts import render
from django.utils.html import strip_tags
from django.views import View
from article.models import Article
import html
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
import re
import xml.etree.ElementTree as etree


# 記事本文は管理者のみが編集できる信頼済みのHTMLのため、本文中の<script>にもCSPのnonceを付与して実行を許可する
def add_csp_nonce(text, nonce):
    return re.sub(r'<script(?=[\s>])', f'<script nonce="{nonce}"', text, flags=re.IGNORECASE)


# マークダウンの画像を横スクロールできる枠（span.article-image）で囲む
# HTMLで直接書かれた画像（Googleドキュメントから書き出した記事など）は独自のレイアウトが崩れないよう対象外にする
class ArticleImageTreeprocessor(Treeprocessor):
    def run(self, root):
        images = [(parent, index) for parent in root.iter() for index, child in enumerate(parent) if child.tag == "img"]
        for parent, index in images:
            image = parent[index]
            wrapper = etree.Element("span", {"class": "article-image"})
            wrapper.tail, image.tail = image.tail, None
            wrapper.append(image)
            parent[index] = wrapper


class ArticleImageExtension(Extension):
    def extendMarkdown(self, md):
        # 画像のimg要素を生成するinline（優先度20）の後に実行する
        md.treeprocessors.register(ArticleImageTreeprocessor(md), "article_image", 15)


class DefaultArticleView(View):
    def get(self, request, id):
        try:
            article = Article.objects.get(pk=id)
        except Article.DoesNotExist:
            return render(request, 'subekashi/404.html', status=404)

        if not article.is_open:
            return render(request, 'subekashi/404.html', status=404)

        # 記事本文がマークダウンかどうかによってMD -> HTMLにする
        text = markdown.markdown(article.text, extensions=['tables', ArticleImageExtension()]) if article.is_md else article.text
        if text:
            text = add_csp_nonce(text, getattr(request, "csp_nonce", ""))

        context = {
            # タイトルはHTMLのため、タブやOGPのタイトルにはタグを除いた文字列を使う（#483）
            "metatitle": html.unescape(strip_tags(article.title)),
            "article": article,
            "text": text
        }
        return render(request, 'article/default_article.html', context)
