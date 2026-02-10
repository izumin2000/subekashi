from django.core.management.base import BaseCommand
from subekashi.models import Song, Author


class Command(BaseCommand):
    help = 'Song.channelフィールドのデータを分析して、Author移行の準備をする'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Song.channelデータ分析 ===\n'))

        # 全曲数
        total_songs = Song.objects.count()
        self.stdout.write(f'総曲数: {total_songs}')

        # channelフィールドが空でない曲数
        songs_with_channel = Song.objects.exclude(channel='').exclude(channel__isnull=True)
        self.stdout.write(f'channelフィールドが設定されている曲数: {songs_with_channel.count()}')

        # ユニークなチャンネル名を収集
        channel_names = set()
        multi_channel_songs = 0

        for song in songs_with_channel:
            channels = song.channel.split(',')
            if len(channels) > 1:
                multi_channel_songs += 1
            for channel in channels:
                channel = channel.strip()
                if channel:
                    channel_names.add(channel)

        self.stdout.write(f'\nユニークなチャンネル名の数: {len(channel_names)}')
        self.stdout.write(f'複数のチャンネルを持つ曲数: {multi_channel_songs}')

        # 既存のAuthorレコード数
        existing_authors = Author.objects.count()
        self.stdout.write(f'\n既存のAuthorレコード数: {existing_authors}')

        # 新規作成が必要なAuthor数を推定
        existing_author_names = set(Author.objects.values_list('name', flat=True))
        new_authors_needed = channel_names - existing_author_names
        self.stdout.write(f'新規作成が必要なAuthor数: {len(new_authors_needed)}')

        # サンプルデータを表示
        self.stdout.write(self.style.SUCCESS('\n=== サンプルデータ（最初の10件） ==='))
        for song in songs_with_channel[:10]:
            self.stdout.write(f'Song ID {song.id}: "{song.title}" - Channel: "{song.channel}"')

        # 複数チャンネルのサンプル
        if multi_channel_songs > 0:
            self.stdout.write(self.style.SUCCESS('\n=== 複数チャンネルのサンプル（最初の5件） ==='))
            count = 0
            for song in songs_with_channel:
                if ',' in song.channel:
                    self.stdout.write(f'Song ID {song.id}: "{song.title}" - Channel: "{song.channel}"')
                    count += 1
                    if count >= 5:
                        break

        self.stdout.write(self.style.SUCCESS('\n分析完了！'))
