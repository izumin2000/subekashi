from config.settings import DEBUG
from django.core.management.base import BaseCommand
from django.conf import settings
from subekashi.models import Song, Author
from article.models import Article
import os
from xml.etree.ElementTree import Element, SubElement, ElementTree
from django.core import management


BASE_URL = "https://lyrics.imicomweb.com"


class Command(BaseCommand):
    help = "subekashi/static/subekashi/にsitemap.xmlを生成する"

    def handle(self, *args, **options):
        sitemap_path = os.path.join(settings.BASE_DIR, "subekashi", "static", "subekashi", "sitemap.xml")

        # ルート要素を作成
        urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
        for loc, priority in self.get_urls():
            self.add_url(urlset, loc, priority)

        # sitemap.xmlファイルの保存
        tree = ElementTree(urlset)
        tree.write(sitemap_path, encoding="utf-8", xml_declaration=True)

        if not DEBUG:
            management.call_command("collectstatic", "--noinput")

        self.stdout.write(self.style.SUCCESS(f"サイトマップを生成しました"))

    def get_urls(self):
        yield f"{BASE_URL}/", "1.0"

        # 優先度が0.9の固定パス
        static_paths = ["/songs/", "/songs/new/", "/stats/", "/ai/", "/ai/result/", "/ad/", "/contact/", "/articles/", "/articles/lilyriku/"]
        for path in static_paths:
            yield BASE_URL + path, "0.9"

        # 優先度が0.8の動的パス (song_id)
        # noindexにしている疑義曲・非公開曲は除外する
        song_ids = Song.objects.filter(is_questionable=False, is_limited=False).values_list('id', flat=True)
        for song_id in song_ids.iterator():
            yield f"{BASE_URL}/songs/{song_id}/", "0.8"
            yield f"{BASE_URL}/songs/{song_id}/history/", "0.5"

        # 優先度が0.8の動的パス (作者)
        for author_id in Author.objects.values_list('id', flat=True).iterator():
            yield f"{BASE_URL}/authors/{author_id}/", "0.8"
            yield f"{BASE_URL}/authors/{author_id}/stats/", "0.6"
            yield f"{BASE_URL}/authors/{author_id}/aliases/", "0.6"

        # 優先度が0.8の動的パス (article_id)
        for article_id in Article.objects.filter(is_open=True).exclude(tag="news").values_list('article_id', flat=True).iterator():
            yield f"{BASE_URL}/articles/{article_id}/", "0.8"

    def add_url(self, urlset, loc, priority):
        url = SubElement(urlset, "url")
        loc_element = SubElement(url, "loc")
        loc_element.text = loc
        priority_element = SubElement(url, "priority")
        priority_element.text = priority
