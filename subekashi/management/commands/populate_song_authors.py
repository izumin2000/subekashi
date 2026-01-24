from django.core.management.base import BaseCommand
from django.db import transaction
from subekashi.models import Song, Author


class Command(BaseCommand):
    help = 'Song.channelからSong.authorsへのデータ移行を行う'

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

        # 統計情報
        total_processed = 0
        total_relations = 0
        songs_with_missing_authors = []
        missing_author_names = set()

        if not dry_run:
            with transaction.atomic():
                for song in songs_with_channel:
                    # カンマで分割（空文字列は除外するが、空白文字のみの場合は保持）
                    channel_names = [name for name in song.channel.split(',') if name]

                    # 各作者名に対応するAuthorオブジェクトを取得
                    authors_to_add = []
                    for channel_name in channel_names:
                        try:
                            author = Author.objects.get(name=channel_name)
                            authors_to_add.append(author)
                        except Author.DoesNotExist:
                            # 作者が見つからない場合は記録
                            songs_with_missing_authors.append((song.id, song.title, channel_name))
                            missing_author_names.add(channel_name)

                    # authorsフィールドに関連付け
                    if authors_to_add:
                        song.authors.set(authors_to_add)
                        total_relations += len(authors_to_add)

                    total_processed += 1

                    # 進捗表示（100曲ごと）
                    if total_processed % 100 == 0:
                        self.stdout.write(f'処理済み: {total_processed}曲...')

                self.stdout.write(self.style.SUCCESS(f'\n[OK] 処理完了'))
                self.stdout.write(f'処理した曲数: {total_processed}')
                self.stdout.write(f'作成した関連付け数: {total_relations}')

                if songs_with_missing_authors:
                    self.stdout.write(self.style.WARNING(f'\n[WARNING] Authorが見つからなかった曲: {len(songs_with_missing_authors)}件'))
                    self.stdout.write(f'見つからなかった作者名: {len(missing_author_names)}個')

                    # サンプルを表示
                    self.stdout.write('\nサンプル（最初の10件）:')
                    for song_id, song_title, author_name in songs_with_missing_authors[:10]:
                        self.stdout.write(f'  Song ID {song_id}: "{song_title}" - 作者名: "{author_name}"')
                else:
                    self.stdout.write(self.style.SUCCESS('\n[OK] すべての作者が正常に関連付けられました'))

        else:
            # ドライランモード
            sample_count = 0
            for song in songs_with_channel[:10]:
                # カンマで分割（空文字列は除外するが、空白文字のみの場合は保持）
                channel_names = [name for name in song.channel.split(',') if name]
                self.stdout.write(f'\nSong ID {song.id}: "{song.title}"')
                self.stdout.write(f'  チャンネル: {song.channel}')
                self.stdout.write(f'  作者数: {len(channel_names)}')

                for channel_name in channel_names:
                    author_exists = Author.objects.filter(name=channel_name).exists()
                    status = "[OK]" if author_exists else "[MISSING]"
                    self.stdout.write(f'    {status} {repr(channel_name)}')

                sample_count += 1

            self.stdout.write(f'\nDRY RUN: {songs_with_channel.count()}曲を処理する予定')
