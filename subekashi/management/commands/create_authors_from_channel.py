from django.core.management.base import BaseCommand
from django.db import transaction
from subekashi.models import Song, Author


class Command(BaseCommand):
    help = 'Song.channelフィールドから一意の作者名を抽出してAuthorテーブルに登録する'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更を加えず、何が起こるかだけを表示する',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))
            self.stdout.write(self.style.WARNING('実際の変更は行われません\n'))

        # channelフィールドが空でない曲を取得
        songs_with_channel = Song.objects.exclude(channel='').exclude(channel__isnull=True)
        self.stdout.write(f'channelフィールドが設定されている曲数: {songs_with_channel.count()}')

        # ユニークなチャンネル名を収集（populate_song_authorsと同じロジック）
        channel_names = set()
        for song in songs_with_channel:
            # カンマで分割して前後の空白を削除（空文字列は除外）
            channels = [name.strip() for name in song.channel.split(',') if name.strip()]
            for channel in channels:
                channel_names.add(channel)

        self.stdout.write(f'抽出されたユニークな作者名数: {len(channel_names)}')

        # 既存のAuthorレコードを確認
        existing_author_names = set(Author.objects.values_list('name', flat=True))
        self.stdout.write(f'既存のAuthorレコード数: {len(existing_author_names)}')

        # 新規作成が必要なAuthor名
        new_author_names = channel_names - existing_author_names
        self.stdout.write(f'新規作成が必要なAuthor数: {len(new_author_names)}')

        if not new_author_names:
            self.stdout.write(self.style.SUCCESS('\n[OK] すべての作者は既に登録されています'))
            return

        # サンプルを表示（最初の10件）
        self.stdout.write(self.style.SUCCESS('\n新規作成する作者名のサンプル（最初の10件）:'))
        for name in sorted(list(new_author_names))[:10]:
            self.stdout.write(f'  - {repr(name)}')

        if dry_run:
            self.stdout.write(f'\nDRY RUN: {len(new_author_names)}件のAuthorレコードを作成する予定')
            return

        # 実際にAuthorレコードを作成
        self.stdout.write('\nAuthorレコードを作成中...')
        with transaction.atomic():
            # 「全てあなたの所為です。」が含まれている場合、ID=1で作成
            special_author_name = '全てあなたの所為です。'
            if special_author_name in new_author_names:
                # 既存のID=1のAuthorを削除（存在する場合）
                Author.objects.filter(id=1).delete()
                # ID=1で「全てあなたの所為です。」を作成
                Author.objects.create(id=1, name=special_author_name)
                self.stdout.write(f'[特別処理] "{special_author_name}" をID=1で作成しました')
                # 残りの作者名から除外
                new_author_names.discard(special_author_name)

            # 残りの作者を一括作成
            if new_author_names:
                authors_to_create = [Author(name=name) for name in new_author_names]
                Author.objects.bulk_create(authors_to_create)

        total_created = len(new_author_names) + (1 if special_author_name in channel_names - existing_author_names else 0)
        self.stdout.write(self.style.SUCCESS(f'\n[OK] {total_created}件のAuthorレコードを作成しました'))

        # 最終確認
        total_authors = Author.objects.count()
        self.stdout.write(f'現在のAuthorレコード総数: {total_authors}')