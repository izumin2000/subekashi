from config.settings import DEBUG
from django.core.management.base import BaseCommand
from django.conf import settings
from subekashi.models import Song
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
        static_paths = ["/ai/", "/song_new/", "/make/", "/songs/", "/setting/", "/ad/", "/special/", "/contact/"]
        for path in static_paths:
            self.add_url(urlset, base_url + path, "0.9")

        # 優先度が0.8の動的パス (song_id)
        songs = Song.objects.all()
        for song in songs:
            # /songs/<int:song_id> のURL
            self.add_url(urlset, f"{base_url}/songs/{song.id}/", "0.8")

        # 優先度が0.8の動的パス (一意のchannel)
        channels_raw = songs.values_list("channel", flat=True)
        channels_set = set([channels for channel_raw in channels_raw for channels in channel_raw.split(",")])  # チャンネルの重複を削除
        for channel in channels_set:
            self.add_url(urlset, f"{base_url}/channel/{channel}/", "0.8")

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
