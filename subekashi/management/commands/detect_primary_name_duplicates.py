from django.core.management.base import BaseCommand
from subekashi.models import Author, AuthorAlias


class Command(BaseCommand):
    help = (
        "alias_type=\"past\"のAuthorAlias.nameが、別の実在するAuthor.nameと衝突している"
        "（＝同一人物が重複して別Authorとして登録されている疑いがある）ケースを検出し、"
        "統合した場合に曲タイトルが重複するSongの組み合わせをレポートする（#1008）。"
        "このコマンドは検出・レポートのみを行い、実際のデータ変更（マージ・削除）は行わない。"
    )

    def handle(self, *args, **options):
        past_aliases = AuthorAlias.objects.filter(alias_type="past").select_related("author")

        found_any = False
        for alias in past_aliases:
            duplicate = Author.objects.filter(name=alias.name).exclude(pk=alias.author_id).first()
            if duplicate is None:
                continue

            found_any = True
            primary = alias.author

            self.stdout.write(self.style.WARNING(
                f"重複候補: Author(id={primary.id}, name='{primary.name}') の"
                f"以前の名称『{alias.name}』が、Author(id={duplicate.id}, name='{duplicate.name}')"
                f"と衝突しています"
            ))

            primary_songs_by_title = {}
            for song in primary.songs.all():
                primary_songs_by_title.setdefault(song.title, []).append(song)

            for song in duplicate.songs.all():
                matching_songs = primary_songs_by_title.get(song.title)
                if matching_songs:
                    matching_ids = ", ".join(str(s.id) for s in matching_songs)
                    self.stdout.write(self.style.ERROR(
                        f"  曲タイトル重複: '{song.title}' "
                        f"(id={song.id}, {duplicate.name}側) が "
                        f"(id={matching_ids}, {primary.name}側) と重複します"
                    ))
                else:
                    self.stdout.write(
                        f"  統合対象曲（重複なし）: '{song.title}' (id={song.id})"
                    )

        if not found_any:
            self.stdout.write(self.style.SUCCESS("重複候補は見つかりませんでした"))
