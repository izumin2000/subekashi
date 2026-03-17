from django.core.management.base import BaseCommand
from django.db import transaction
from subekashi.models import Song, SongLink

SAMPLE_SIZE = 10


class Command(BaseCommand):
    help = 'Song.urlからSongLinkへのデータ移行を行う'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には変更を加えず、何が起こるかだけを表示する',
        )
        parser.add_argument(
            '--song-id',
            type=int,
            default=None,
            help='特定のSong IDのみ処理する',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        song_id = options['song_id']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE ==='))
            self.stdout.write(self.style.WARNING('実際の変更は行われません\n'))

        songs = Song.objects.exclude(url='').exclude(url__isnull=True)
        if song_id:
            songs = songs.filter(id=song_id)

        self.stdout.write(f'処理対象曲数: {songs.count()}')

        if dry_run:
            self._dry_run(songs)
        else:
            self._migrate(songs)

    def _dry_run(self, songs):
        already_migrated = 0
        total_urls = 0

        for song in songs:
            if song.links.exists():
                already_migrated += 1
                continue
            urls = [u.strip() for u in song.url.split(',') if u.strip()]
            total_urls += len(urls)

        self.stdout.write(f'移行済み（スキップ予定）: {already_migrated}曲')
        self.stdout.write(f'作成予定SongLink数: {total_urls}件')

        sample = []
        for song in songs:
            if not song.links.exists():
                sample.append(song)
            if len(sample) >= SAMPLE_SIZE:
                break

        if sample:
            self.stdout.write(f'\nサンプル（最大{SAMPLE_SIZE}件）:')
            for song in sample:
                urls = [u.strip() for u in song.url.split(',') if u.strip()]
                self.stdout.write(f'  Song ID {song.id}: {len(urls)}件のURL')
                for url in urls:
                    existing = SongLink.objects.filter(url=url).first()
                    dup_note = ' [重複→allow_dup=True]' if existing and existing.songs.exclude(pk=song.pk).exists() else ''
                    self.stdout.write(f'    - {url}{dup_note}')

    def _migrate(self, songs):
        total_created = 0
        total_skipped = 0
        total_allow_dup = 0

        with transaction.atomic():
            for song in songs:
                if song.links.exists():
                    total_skipped += 1
                    continue

                urls = [u.strip() for u in song.url.split(',') if u.strip()]
                if not urls:
                    total_skipped += 1
                    continue

                for url in urls:
                    link, created = SongLink.objects.get_or_create(url=url)
                    if not created and link.songs.exclude(pk=song.pk).exists():
                        # 別の曲が既にこのURLを使用している → 重複
                        link.allow_dup = True
                        link.save()
                        total_allow_dup += 1
                    link.songs.add(song)
                total_created += len(urls)

                processed = total_created + total_skipped
                if processed % 100 == 0:
                    self.stdout.write(f'処理済み: {processed}件...')

        self.stdout.write(self.style.SUCCESS('\n[OK] 処理完了'))
        self.stdout.write(f'作成したSongLink数: {total_created}')
        self.stdout.write(f'スキップした曲数: {total_skipped}')
        self.stdout.write(f'allow_dup=Trueに設定したSongLink数: {total_allow_dup}')
