from django.core.management.base import BaseCommand
from django.db import models as django_models
from subekashi.models import Song, Author


class Command(BaseCommand):
    help = 'Song.authorsフィールドのデータ整合性を検証する'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Song.authors検証 ===\n'))

        # 統計情報
        total_songs = Song.objects.count()
        songs_with_channel = Song.objects.exclude(channel='').exclude(channel__isnull=True)
        songs_with_authors = Song.objects.filter(authors__isnull=False).distinct()

        self.stdout.write(f'総曲数: {total_songs}')
        self.stdout.write(f'channelフィールドが設定されている曲数: {songs_with_channel.count()}')
        self.stdout.write(f'authorsフィールドが設定されている曲数: {songs_with_authors.count()}')

        # channelがあるがauthorsがない曲を検出
        songs_with_channel_no_authors = songs_with_channel.filter(authors__isnull=True)
        if songs_with_channel_no_authors.exists():
            self.stdout.write(self.style.WARNING(f'\n[WARNING] channelはあるがauthorsがない曲: {songs_with_channel_no_authors.count()}件'))

            # サンプルを表示
            self.stdout.write('\nサンプル（最初の10件）:')
            for song in songs_with_channel_no_authors[:10]:
                self.stdout.write(f'  Song ID {song.id}: "{song.title}" - Channel: "{song.channel}"')
        else:
            self.stdout.write(self.style.SUCCESS('\n[OK] すべてのchannelがauthorsに変換されています'))

        # authorsとchannelの数を比較
        self.stdout.write(self.style.SUCCESS('\n=== 作者数の比較 ==='))

        mismatches = []
        sample_count = 0
        for song in songs_with_channel[:100]:  # サンプルとして100曲チェック
            channel_count = len([c.strip() for c in song.channel.split(',') if c.strip()])
            authors_count = song.authors.count()

            if channel_count != authors_count:
                mismatches.append({
                    'id': song.id,
                    'title': song.title,
                    'channel': song.channel,
                    'channel_count': channel_count,
                    'authors_count': authors_count
                })

            sample_count += 1

        if mismatches:
            self.stdout.write(self.style.WARNING(f'\n[WARNING] 作者数が一致しない曲（サンプル100曲中）: {len(mismatches)}件'))

            # サンプルを表示
            self.stdout.write('\nサンプル（最初の5件）:')
            for mismatch in mismatches[:5]:
                self.stdout.write(f'  Song ID {mismatch["id"]}: "{mismatch["title"]}"')
                self.stdout.write(f'    Channel: "{mismatch["channel"]}"')
                self.stdout.write(f'    Channel count: {mismatch["channel_count"]}, Authors count: {mismatch["authors_count"]}')
        else:
            self.stdout.write(self.style.SUCCESS(f'[OK] サンプル{sample_count}曲の作者数が一致しています'))

        # 複数作者の曲の統計
        multi_author_songs = Song.objects.annotate(
            author_count=django_models.Count('authors')
        ).filter(author_count__gt=1)

        self.stdout.write(self.style.SUCCESS('\n=== 複数作者の曲 ==='))
        self.stdout.write(f'複数作者の曲数: {multi_author_songs.count()}')

        # サンプル表示
        self.stdout.write('\nサンプル（最初の5件）:')
        for song in multi_author_songs[:5]:
            author_names = ', '.join([a.name for a in song.authors.all()])
            self.stdout.write(f'  Song ID {song.id}: "{song.title}"')
            self.stdout.write(f'    Authors: {author_names}')

        self.stdout.write(self.style.SUCCESS('\n検証完了'))
