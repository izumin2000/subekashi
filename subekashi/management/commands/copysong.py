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
        try:
            with urllib.request.urlopen(req) as res:
                body = json.load(res)
        except urllib.error.HTTPError as e:
            self.stdout.write(self.style.ERROR(f"リクエスト中にエラーが発生しました。\n{e.code} {e.reason}"))
            return
        result = body['result']
        self.stdout.write(self.style.SUCCESS(f"{len(result)}曲を取得しました。"))
        songs = []
        for songjson in result:
            song = self.json_to_song(songjson)
            if(song is not None): songs.append(song)
        Song.objects.bulk_create(songs)
        self.stdout.write(self.style.SUCCESS(f"処理が完了しました。"))

    def request_song(self,id):
        req_url = self.original_song_api + str(id)
        self.stdout.write("データを取得中です...")
        req = urllib.request.Request(req_url)
        try:
            with urllib.request.urlopen(req) as res:
                result = json.load(res)
        except urllib.error.HTTPError as e:
            if(e.code == 404):
                self.stdout.write(self.style.ERROR(f"ID {id}は登録されていない曲です。"))
            else:
                self.stdout.write(self.style.ERROR(f"リクエスト中にエラーが発生しました。\n{e.code} {e.reason}"))
            return 
        self.stdout.write(self.style.SUCCESS(f"{result['title']}を取得しました。"))
        song = self.json_to_song(result)
        if(song is not None): song.save()
            

    def json_to_song(self,songjson:Dict):
        if(Song.objects.filter(pk=songjson["id"]).exists()):
            self.stdout.write(self.style.ERROR(f"ID {songjson['id']}はすでに存在しています。"))
            return
        
        song = Song(**songjson)
        return song

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