from django.core.management.base import BaseCommand
from subekashi.models import Song


class Command(BaseCommand):
    help = "imitate CharField から imitates ManyToManyField にデータを移植する"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='実際には保存せず、移植内容をログ出力のみ行う',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING("=== DRY RUN モード（保存は行いません）==="))

        total = 0
        skipped = 0

        for song in Song.objects.iterator():
            if not song.imitate:
                continue

            ids = []
            for raw in song.imitate.split(","):
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    ids.append(int(raw))
                except ValueError:
                    self.stdout.write(self.style.WARNING(
                        f"  [{song.id}] 不正な値をスキップ: '{raw}'"
                    ))

            if not ids:
                continue

            targets = []
            for target_id in ids:
                try:
                    targets.append(Song.objects.get(pk=target_id))
                except Song.DoesNotExist:
                    self.stdout.write(self.style.WARNING(
                        f"  [{song.id}] 存在しないsong_idをスキップ: {target_id}"
                    ))
                    skipped += 1

            if not targets:
                continue

            if not dry_run:
                song.imitates.set(targets)

            total += 1
            if total % 100 == 0:
                self.stdout.write(f"{total}件の模倣関係を処理しました")

        self.stdout.write(self.style.SUCCESS(
            f"\n完了: {total}件移植, {skipped}件スキップ"
        ))
