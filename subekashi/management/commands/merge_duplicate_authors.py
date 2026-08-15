from django.core.management.base import BaseCommand
from django.db import transaction
from subekashi.models import Author, AuthorAlias, AuthorLink


class Command(BaseCommand):
    help = (
        "同一人物が重複して別々のAuthor行として登録されている場合に、"
        "duplicate側の情報（Song・AuthorLink・AuthorAlias）を全てprimary側に付け替えた上で、"
        "duplicate Authorを削除して統合する（#1029）。"
        "統合すると曲タイトルが重複するSongが1件でもある場合は、統合を一切行わず中止する。"
    )

    def add_arguments(self, parser):
        parser.add_argument('primary_id', type=int, help="統合後に残すAuthorのid")
        parser.add_argument('duplicate_id', type=int, help="統合により削除するAuthorのid")

    def handle(self, *args, **options):
        primary_id = options['primary_id']
        duplicate_id = options['duplicate_id']

        if primary_id == duplicate_id:
            self.stdout.write(self.style.ERROR("primary_idとduplicate_idに同じidが指定されています。"))
            return

        primary = Author.get_or_none(primary_id)
        if primary is None:
            self.stdout.write(self.style.ERROR(f"Author(id={primary_id})は存在しません。"))
            return

        duplicate = Author.get_or_none(duplicate_id)
        if duplicate is None:
            self.stdout.write(self.style.ERROR(f"Author(id={duplicate_id})は存在しません。"))
            return

        primary_songs_by_title = {}
        for song in primary.songs.all():
            primary_songs_by_title.setdefault(song.title, []).append(song)

        duplicate_songs = list(duplicate.songs.all())
        colliding_titles = [song for song in duplicate_songs if song.title in primary_songs_by_title]
        if colliding_titles:
            self.stdout.write(self.style.ERROR(
                f"Author(id={primary.id}, name='{primary.name}')とAuthor(id={duplicate.id}, "
                f"name='{duplicate.name}')の統合を中止しました。曲タイトルが重複するSongがあります。"
            ))
            for song in colliding_titles:
                matching_ids = ", ".join(str(s.id) for s in primary_songs_by_title[song.title])
                self.stdout.write(self.style.ERROR(
                    f"  '{song.title}' (id={song.id}, {duplicate.name}側) が "
                    f"(id={matching_ids}, {primary.name}側) と重複します"
                ))
            return

        with transaction.atomic():
            for song in duplicate_songs:
                song.authors.add(primary)
            AuthorLink.objects.filter(author=duplicate).update(author=primary)
            AuthorAlias.objects.filter(author=duplicate).update(author=primary)
            duplicate.delete()

        self.stdout.write(self.style.SUCCESS(
            f"Author(id={duplicate_id}, name='{duplicate.name}')をAuthor(id={primary_id}, "
            f"name='{primary.name}')に統合しました。"
            f"（Song {len(duplicate_songs)}件を付け替え、duplicateを削除しました）"
        ))
