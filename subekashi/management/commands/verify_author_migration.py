from django.core.management.base import BaseCommand
from subekashi.models import Song, Author


class Command(BaseCommand):
    help = 'Author移行の整合性を検証する'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Author移行の検証 ===\n'))

        # Authorレコードの総数
        total_authors = Author.objects.count()
        self.stdout.write(f'総Author数: {total_authors}')

        # channelフィールドから期待されるAuthor名を収集
        songs_with_channel = Song.objects.exclude(channel='').exclude(channel__isnull=True)
        expected_author_names = set()

        for song in songs_with_channel:
            channels = song.channel.split(',')
            for channel in channels:
                channel = channel.strip()
                if channel:
                    expected_author_names.add(channel)

        self.stdout.write(f'期待されるAuthor数: {len(expected_author_names)}')

        # 不足しているAuthorをチェック
        existing_author_names = set(Author.objects.values_list('name', flat=True))
        missing_authors = expected_author_names - existing_author_names

        if missing_authors:
            self.stdout.write(self.style.ERROR(f'\n[ERROR] 不足しているAuthor: {len(missing_authors)}'))
            for name in list(missing_authors)[:10]:
                self.stdout.write(f'  - {name}')
            if len(missing_authors) > 10:
                self.stdout.write(f'  ... 他 {len(missing_authors) - 10}件')
        else:
            self.stdout.write(self.style.SUCCESS('\n[OK] すべてのAuthorが存在します'))

        # 余分なAuthorをチェック（Song.channelに存在しないAuthor）
        extra_authors = existing_author_names - expected_author_names

        if extra_authors:
            self.stdout.write(self.style.WARNING(f'\n[WARNING] Song.channelに存在しないAuthor: {len(extra_authors)}'))
            for name in list(extra_authors)[:10]:
                self.stdout.write(f'  - {name}')
            if len(extra_authors) > 10:
                self.stdout.write(f'  ... 他 {len(extra_authors) - 10}件')
        else:
            self.stdout.write('\n[OK] 余分なAuthorはありません')

        # 統計情報
        self.stdout.write(self.style.SUCCESS('\n=== 統計情報 ==='))
        self.stdout.write(f'channelフィールドが設定されている曲数: {songs_with_channel.count()}')

        multi_channel_songs = 0
        for song in songs_with_channel:
            if ',' in song.channel:
                multi_channel_songs += 1

        self.stdout.write(f'複数のAuthorを持つ曲数: {multi_channel_songs}')

        if missing_authors:
            self.stdout.write(self.style.ERROR('\n検証失敗: 不足しているAuthorがあります'))
        else:
            self.stdout.write(self.style.SUCCESS('\n検証成功'))
