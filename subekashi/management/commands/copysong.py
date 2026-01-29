from django.core.management.base import BaseCommand
from subekashi.models import Song, Author
from typing import Dict
import urllib.request
import json

# TODO 本番環境にAuthorを適用後copysongカスタムコマンドの動作確認
class Command(BaseCommand):
    help = "公開環境のすべかしから指定した曲またはすべての曲をコピーする。すでにあるファイルは上書きしない。"
    original_song_api = "https://lyrics.imicomweb.com/api/song/"

    def request_all_songs(self):
        prompted = input("大量の曲を取得しようとしています。続行しますか？(Y/n) ")
        if (prompted == "n") or (prompted == "no"):
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
        all_authors_data = []
        for songjson in result:
            song = self.json_to_song(songjson)
            if song is not None:
                songs.append(song)
                if hasattr(song, '_authors_data'):
                    all_authors_data.extend(song._authors_data)

        # Songを一括作成
        Song.objects.bulk_create(songs)
        self.stdout.write(self.style.SUCCESS(f"{len(songs)}曲を作成しました。"))

        # Authorを一括作成
        self.stdout.write("Authorsを作成中です...")
        unique_authors = {(a['id'], a['name']) for a in all_authors_data}
        authors_to_create = []
        for author_id, name in unique_authors:
            if not Author.objects.filter(id=author_id).exists():
                authors_to_create.append(Author(id=author_id, name=name))

        if authors_to_create:
            Author.objects.bulk_create(authors_to_create, ignore_conflicts=True)
            self.stdout.write(f"  {len(authors_to_create)}件のAuthorを作成しました。")

        # Song-Author関係を一括作成
        self.stdout.write("Song-Author関係を設定中です...")
        song_authors = []
        for song in songs:
            if hasattr(song, '_authors_data'):
                for author_data in song._authors_data:
                    song_authors.append(
                        Song.authors.through(
                            song_id=song.id,
                            author_id=author_data['id']
                        )
                    )

        if song_authors:
            Song.authors.through.objects.bulk_create(song_authors, ignore_conflicts=True)
            self.stdout.write(f"  {len(song_authors)}件の関係を作成しました。")

        self.stdout.write(self.style.SUCCESS(f"処理が完了しました。"))

    def request_song(self, id):
        req_url = self.original_song_api + str(id)
        self.stdout.write("データを取得中です...")
        req = urllib.request.Request(req_url)
        try:
            with urllib.request.urlopen(req) as res:
                result = json.load(res)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.stdout.write(self.style.ERROR(f"ID {id}は登録されていない曲です。"))
            else:
                self.stdout.write(self.style.ERROR(f"リクエスト中にエラーが発生しました。\n{e.code} {e.reason}"))
            return
        self.stdout.write(self.style.SUCCESS(f"{result['title']}を取得しました。"))
        song = self.json_to_song(result)
        if song is not None:
            song.save()
            # authorsを設定
            self._set_song_authors(song)
            

    def _set_song_authors(self, song):
        """Songにauthorsを設定する"""
        if song is None:
            return
        if not hasattr(song, '_authors_data'):
            return

        for author_data in song._authors_data:
            # AuthorをIDとnameで取得または作成
            author, created = Author.objects.get_or_create(
                id=author_data['id'],
                defaults={'name': author_data['name']}
            )
            if created:
                self.stdout.write(f"  Author ID={author.id}: {author.name} を作成しました。")
            song.authors.add(author)

    def json_to_song(self, songjson: Dict):
        if Song.objects.filter(pk=songjson["id"]).exists():
            self.stdout.write(self.style.ERROR(f"ID {songjson['id']}はすでに存在しています。"))
            return None

        # authorsフィールドを分離（ManyToManyFieldは保存後に設定する必要がある）
        authors_data = songjson.pop('authors', [])

        # Songオブジェクトを作成
        song = Song(**songjson)

        # authorsデータを一時的に保存（保存後に設定するため）
        song._authors_data = authors_data

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