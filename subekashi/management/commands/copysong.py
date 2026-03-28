from django.core.management.base import BaseCommand
from subekashi.models import Song, Author, SongLink
from typing import Dict
import urllib.request
import json

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
        for songjson in result:
            song = self.json_to_song(songjson)
            if song is not None:
                songs.append(song)

        # Songを一括作成
        Song.objects.bulk_create(songs)
        self.stdout.write(self.style.SUCCESS(f"{len(songs)}曲を作成しました。"))

        # 全songのauthor名・URLを収集
        author_name_to_songs = {}
        url_to_songs = {}
        for song in songs:
            for author_data in getattr(song, '_authors_data', []):
                author_name_to_songs.setdefault(author_data['name'], []).append(song)
            for url in getattr(song, '_urls_data', []):
                url_to_songs.setdefault(url, []).append(song)

        # Authorを一括作成（get_or_createと同等）
        self.stdout.write("Author関係を設定中です...")
        all_names = set(author_name_to_songs.keys())
        existing_names = set(Author.objects.filter(name__in=all_names).values_list('name', flat=True))
        new_authors = [Author(name=name) for name in all_names if name not in existing_names]
        if new_authors:
            Author.objects.bulk_create(new_authors, ignore_conflicts=True)
            self.stdout.write(f"  {len(new_authors)}件のAuthorを作成しました。")
        name_to_author = {a.name: a for a in Author.objects.filter(name__in=all_names)}
        song_author_rows = [
            Song.authors.through(song_id=song.id, author_id=name_to_author[name].id)
            for name, songs_for_name in author_name_to_songs.items()
            for song in songs_for_name
            if name in name_to_author
        ]
        if song_author_rows:
            Song.authors.through.objects.bulk_create(song_author_rows, ignore_conflicts=True)

        # SongLinkを一括作成（get_or_createと同等）
        self.stdout.write("SongLink関係を設定中です...")
        all_urls = set(url_to_songs.keys())
        existing_urls = set(SongLink.objects.filter(url__in=all_urls).values_list('url', flat=True))
        new_links = [SongLink(url=url) for url in all_urls if url not in existing_urls]
        if new_links:
            SongLink.objects.bulk_create(new_links, ignore_conflicts=True)
            self.stdout.write(f"  {len(new_links)}件のSongLinkを作成しました。")
        url_to_link = {l.url: l for l in SongLink.objects.filter(url__in=all_urls)}
        song_link_rows = [
            SongLink.songs.through(songlink_id=url_to_link[url].id, song_id=song.id)
            for url, songs_for_url in url_to_songs.items()
            for song in songs_for_url
            if url in url_to_link
        ]
        if song_link_rows:
            SongLink.songs.through.objects.bulk_create(song_link_rows, ignore_conflicts=True)

        # imitates関係を一括作成（全Song作成済みのためスキップ不要）
        self.stdout.write("imitates関係を設定中です...")
        all_song_ids = set(Song.objects.values_list('id', flat=True))
        imitate_rows = [
            Song.imitates.through(from_song_id=song.id, to_song_id=target_id)
            for song in songs
            for target_id in getattr(song, '_imitates_data', [])
            if target_id in all_song_ids
        ]
        if imitate_rows:
            Song.imitates.through.objects.bulk_create(imitate_rows, ignore_conflicts=True)
            self.stdout.write(f"  {len(imitate_rows)}件のimitates関係を作成しました。")

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
            # SongLinkを設定
            self._set_song_links(song)
            # imitatesを設定（参照先が存在しない場合はスキップ）
            self._set_song_imitates(song)
            

    def _set_song_authors(self, song):
        """Songにauthorsを設定する"""
        if song is None:
            return
        if not hasattr(song, '_authors_data'):
            return

        for author_data in song._authors_data:
            # nameはUNIQUEなのでnameで取得または作成
            author, created = Author.objects.get_or_create(
                name=author_data['name'],
            )
            song.authors.add(author)

    def _set_song_links(self, song):
        """SongにSongLinkを設定する"""
        if song is None:
            return
        if not hasattr(song, '_urls_data'):
            return

        for url in song._urls_data:
            link, _ = SongLink.objects.get_or_create(url=url)
            link.songs.add(song)

    def _set_song_imitates(self, song):
        """Songにimitatesを設定する（存在しないIDはスキップ）"""
        if song is None:
            return
        if not hasattr(song, '_imitates_data') or not song._imitates_data:
            return

        for target_id in song._imitates_data:
            try:
                target = Song.objects.get(pk=target_id)
                song.imitates.add(target)
            except Song.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  [{song.id}] 模倣元ID {target_id} はローカルに存在しないためスキップしました。"
                ))

    def json_to_song(self, songjson: Dict):
        if Song.objects.filter(pk=songjson["id"]).exists():
            self.stdout.write(self.style.ERROR(f"ID {songjson['id']}はすでに存在しています。"))
            return None

        # authorsフィールドを分離（ManyToManyFieldは保存後に設定する必要がある）
        authors_data = songjson.pop('authors', [])

        # urlはSongモデルのフィールドではなくSongLinkで管理するため分離
        urls_data = songjson.pop('url', [])

        # imitates/imitatedsはManyToManyFieldのため保存後に設定する必要がある
        imitates_data = songjson.pop('imitates', [])
        songjson.pop('imitateds', [])  # 逆参照は imitates から自動管理されるため不要

        # Songオブジェクトを作成
        song = Song(**songjson)

        # authors/urls/imitatesデータを一時的に保存（保存後に設定するため）
        song._authors_data = authors_data
        # 旧API: url は "url1,url2" 形式の文字列、新API: リスト
        if isinstance(urls_data, list):
            song._urls_data = urls_data
        elif isinstance(urls_data, str) and urls_data:
            song._urls_data = [u.strip() for u in urls_data.split(',') if u.strip()]
        else:
            song._urls_data = []
        song._imitates_data = imitates_data if isinstance(imitates_data, list) else []

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