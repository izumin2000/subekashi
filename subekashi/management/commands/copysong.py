from django.core.management.base import BaseCommand
from subekashi.models import Song
from typing import Dict, List
import urllib.request
import json

class Command(BaseCommand):
    help = "公開環境のすべかしから指定した曲またはすべての曲をコピーする。すでにあるファイルは上書きしない。"
    original_song_api = "https://lyrics.imicomweb.com/api/song/"

    def request_all_songs(self):
        prompted = input("大量の曲を取得しようとしています。続行しますか？(Y/n) ")
        if(prompted == "n" or prompted == "no"): 
            return
        allsongs_url = self.original_song_api + "?size=2147483647"
        self.stdout.write("データを取得中です...(これには時間がかかります)")
        req = urllib.request.Request(allsongs_url)
        with urllib.request.urlopen(req) as res:
            body = json.load(res)
        result = body['result']
        self.stdout.write(self.style.SUCCESS(f"{len(result)}曲を取得しました。"))
        for song in result:
            self.register_song(song)
        self.stdout.write(self.style.SUCCESS(f"処理が完了しました。"))

    def request_song(self,id):
        req_url = self.original_song_api + str(id)
        self.stdout.write("データを取得中です...")
        req = urllib.request.Request(req_url)
        with urllib.request.urlopen(req) as res:
            result = json.load(res)
        self.stdout.write(self.style.SUCCESS(f"{result['title']}を取得しました。"))
        self.register_song(result)
            

    def register_song(self,songjson:Dict):
        if(Song.objects.filter(pk=songjson["id"]).exists()):
            self.stdout.write(self.style.ERROR(f"ID {songjson['id']}はすでに存在しています。"))
            return
        
        song = Song(
            id = songjson["id"],
            title = songjson["title"],
            channel = songjson["channel"],
            url = songjson["url"],
            lyrics = songjson["lyrics"],
            imitate = songjson["imitate"],
            imitated = songjson["imitated"],
            post_time = songjson["post_time"],
            upload_time = songjson["upload_time"],
            isoriginal = songjson["isoriginal"],
            isjoke = songjson["isjoke"],
            isdeleted = songjson["isdeleted"],
            isdraft = songjson["isdraft"],
            isinst = songjson["isinst"],
            issubeana = songjson["issubeana"],
            isspecial = songjson["isspecial"],
            islock = songjson["islock"],
            view = songjson["view"],
            like = songjson["like"],
            category = songjson["category"],
        )
        song.save()

    def handle(self, *args, **options):
        
        id = options['id']
        all = options['all']
        if(id is None and not all):
            self.stdout.write(self.style.ERROR_OUTPUT("--id ID または --all が指定されていません。"))
            return
        if(all):
            self.request_all_songs()
        else:
            self.request_song(id)

    def add_arguments(self, parser):
        parser.add_argument(
            '--id',
            type=int,
        )
        parser.add_argument(
            '--all',
            action="store_true",
        )