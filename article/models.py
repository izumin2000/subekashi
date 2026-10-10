from django.db import models
from django.db.models import Q
from django.utils import timezone
import markdown
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor


# タイトルは見出しやリンクの中に表示するため、1つの段落だけのときはp要素で囲まない
# （p要素のフォントサイズが適用されて記事ページの見出しが小さくなるのを防ぐ）
class UnwrapParagraphTreeprocessor(Treeprocessor):
    def run(self, root):
        if len(root) != 1 or root[0].tag != "p":
            return
        paragraph = root[0]
        children = list(paragraph)
        root.remove(paragraph)
        root.text = paragraph.text
        root.extend(children)


class UnwrapParagraphExtension(Extension):
    def extendMarkdown(self, md):
        # 太字やリンクの要素を生成するinline（優先度20）の後に実行する
        md.treeprocessors.register(UnwrapParagraphTreeprocessor(md), "unwrap_paragraph", 15)


class Article(models.Model) :
    TAGS = (
        ("news", "ニュース"),
        ("release", "リリースノート"),
        ("howto", "使い方"),
        ("blog", "ブログ"),
        ("tool", "ツール"),
        ("tech", "技術"),
        ("other", "その他"),
    )
    article_id = models.CharField(default = "", max_length = 100, primary_key=True)
    title = models.CharField(default = "", max_length = 500)
    author = models.CharField(default = "", max_length = 50)
    tag = models.CharField(default = "", choices=TAGS, max_length=10)
    text = models.TextField(default = "", blank = True, null = True, max_length = 1000000)
    post_time = models.DateTimeField(blank = True, null = True)
    is_open = models.BooleanField(default = True)
    is_md = models.BooleanField(default = True)
    handle_as_news = models.BooleanField(default = False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # マークダウンの記事はタイトルも登録時にHTMLへ変換する（#483）
        # 変換後のHTMLを再度変換しても変わらないため、保存し直してもタイトルは崩れない
        if self.is_md:
            self.title = markdown.markdown(self.title, extensions=[UnwrapParagraphExtension()])
        super().save(*args, **kwargs)

    @classmethod
    def get_top_news_articles(cls):
        """トップページ用のニュース・リリース記事を返す"""
        return cls.objects.filter(
            is_open=True
        ).filter(
            (Q(tag="news") | Q(tag="release") | Q(handle_as_news=True)) &
            Q(post_time__lte=timezone.now())
        ).order_by("-post_time")[:3]
