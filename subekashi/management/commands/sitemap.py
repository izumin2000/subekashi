from config.settings import DEBUG
from django.core.management.base import BaseCommand
from django.conf import settings
from subekashi.models import Song, Author
from article.models import Article
import os
from xml.etree.ElementTree import Element, SubElement, ElementTree
from django.core import management


class Command(BaseCommand):
    help = "subekashi/static/subekashi/にsitemap.xmlを生成する"

    def handle(self, *args, **options):
        sitemap_path = os.path.join(settings.BASE_DIR, "subekashi", "static", "subekashi", "sitemap.xml")

        # ルート要素を作成
        urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        base_url = "https://lyrics.imicomweb.com"
        self.add_url(urlset, base_url + "/", "1.0")

        # 優先度が0.9の固定パス
        static_paths = ["/ai/", "/songs/", "/songs/new/", "/ai/", "/ai/result/", "/ad/", "/contact/", "/articles/"]
        for path in static_paths:
            self.add_url(urlset, base_url + path, "0.9")

        # 優先度が0.8の動的パス (song_id)
        for song_id in Song.objects.values_list('id', flat=True).iterator():
            # /songs/<int:song_id> のURL
            self.add_url(urlset, f"{base_url}/songs/{song_id}/", "0.8")

        # 優先度が0.8の動的パス (作者)
        for author_id, author_name in Author.objects.values_list('id', 'name').iterator():
            # /author/<int:author_id> のURL（新形式）
            self.add_url(urlset, f"{base_url}/author/{author_id}/", "0.8")
            # /channel/<str:author_name> のURL（旧形式、リダイレクトのため維持）
            self.add_url(urlset, f"{base_url}/channel/{author_name}/", "0.7")

        # 優先度が0.8の動的パス (article_id)
        for article_id in Article.objects.filter(is_open=True).exclude(tag="news").values_list('article_id', flat=True).iterator():
            # /articles/<str:article_id> のURL
            self.add_url(urlset, f"{base_url}/articles/{article_id}/", "0.8")

        # sitemap.xmlファイルの保存
        tree = ElementTree(urlset)
        tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)

        if not DEBUG:
            management.call_command("collectstatic", "--noinput")
        
        self.stdout.write(self.style.SUCCESS(f"サイトマップを生成しました"))

    def add_url(self, urlset, loc, priority):
        url = SubElement(urlset, "url")
        loc_element = SubElement(url, "loc")
        loc_element.text = loc
        priority_element = SubElement(url, "priority")
        priority_element.text = priority
