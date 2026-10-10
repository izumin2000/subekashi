from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags
from article.lib.html_utils import remove_links
from article.lib.markdown_extensions import UnwrapParagraphExtension
import html
import markdown


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
        return self.plain_title

    # タイトルはHTMLのため、管理画面やタブ・OGPのタイトルにはタグを除いた文字列を使う
    @property
    def plain_title(self):
        return html.unescape(strip_tags(self.title))

    def convert_title(self):
        # マークダウンの記事はタイトルもHTMLへ変換する（#483）
        # 変換後のHTMLを再度変換しても変わらないため、保存し直してもタイトルは崩れない
        if not self.is_md:
            return self.title
        return markdown.markdown(self.title, extensions=[UnwrapParagraphExtension()])

    def clean(self):
        # HTMLに変換するとタグの分だけ文字数が増えるため、上限を超える場合は保存時のDBのエラーではなく入力エラーにする
        max_length = self._meta.get_field("title").max_length
        title_length = len(self.convert_title())
        if title_length > max_length:
            raise ValidationError({"title": f"HTMLに変換すると{title_length}文字になり、上限の{max_length}文字を超えます。"})

    def save(self, *args, **kwargs):
        self.title = self.convert_title()
        super().save(*args, **kwargs)

    @property
    def title_without_links(self):
        # 記事へのリンクの中にタイトルを表示するとき、<a>が入れ子にならないようタイトル中のリンクのタグだけを外す
        return remove_links(self.title)

    @classmethod
    def get_top_news_articles(cls):
        """トップページ用のニュース・リリース記事を返す"""
        return cls.objects.filter(
            is_open=True
        ).filter(
            (Q(tag="news") | Q(tag="release") | Q(handle_as_news=True)) &
            Q(post_time__lte=timezone.now())
        ).order_by("-post_time")[:3]
