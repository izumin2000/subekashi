from django.core.management.base import BaseCommand
from django.db import transaction
from subekashi.models import Song, Author


class Command(BaseCommand):
    help = 'Song.channelからAuthorレコードを作成し、将来的なManyToManyField移行の準備をする'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更を加えず、何が起こるかだけを表示する',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='処理する曲数の上限（テスト用）',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))
            self.stdout.write(self.style.WARNING('実際の変更は行われません\n'))

        # channelフィールドが設定されている曲を取得
        songs_with_channel = Song.objects.exclude(channel='').exclude(channel__isnull=True)

        if limit:
            songs_with_channel = songs_with_channel[:limit]
            self.stdout.write(f'処理対象曲数: {limit}（制限付き）')
        else:
            self.stdout.write(f'処理対象曲数: {songs_with_channel.count()}')

        # ユニークなチャンネル名を収集
        channel_names = set()
        for song in songs_with_channel:
            channels = song.channel.split(',')
            for channel in channels:
                channel = channel.strip()
                if channel:
                    channel_names.add(channel)

        self.stdout.write(f'ユニークなチャンネル名の数: {len(channel_names)}\n')

        if not dry_run:
            with transaction.atomic():
                # Authorレコードを作成
                created_count = 0
                existing_count = 0

                for channel_name in channel_names:
                    author, created = Author.objects.get_or_create(name=channel_name)
                    if created:
                        created_count += 1
                    else:
                        existing_count += 1

                self.stdout.write(self.style.SUCCESS(f'[OK] 新規Authorレコード作成: {created_count}'))
                self.stdout.write(f'既存Authorレコード: {existing_count}')
                self.stdout.write(self.style.SUCCESS('\n移行完了'))
        else:
            self.stdout.write(f'DRY RUN: {len(channel_names)}個のAuthorレコードを作成する予定')

            # サンプルを表示
            sample_names = list(channel_names)[:10]
            self.stdout.write('\nサンプル（最初の10件）:')
            for name in sample_names:
                self.stdout.write(f'  - {name}')
