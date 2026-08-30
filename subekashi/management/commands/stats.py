from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from subekashi.lib.stats_service import (
    compute_common_stats,
    month_start,
    next_year_month,
)
from subekashi.models import Song, Stats


class Command(BaseCommand):
    help = "月次統計(Stats)の集計・保存。最古のSongの月〜今月までを毎回再計算する"

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='日付ガードを無視して強制実行する（デプロイ時の過去分バックフィル用）',
        )

    def handle(self, *args, **options):
        now = datetime.now()
        if now.day != 1 and not options['force']:
            return

        first_song = Song.objects.exclude(upload_time__isnull=True).order_by('upload_time').first()
        if first_song is None:
            return

        # DBにはUTCで保存されているため、月の境界はローカルタイムゾーンに変換してから判定する
        first_local = timezone.localtime(first_song.upload_time)
        year, month = first_local.year, first_local.month
        current_year, current_month = now.year, now.month

        while (year, month) <= (current_year, current_month):
            next_year, next_month = next_year_month(year, month)
            qs = Song.objects.filter(upload_time__lt=month_start(next_year, next_month))
            Stats.objects.update_or_create(
                year=year,
                month=month,
                defaults=compute_common_stats(qs),
            )
            year, month = next_year, next_month

        self.stdout.write(self.style.SUCCESS("月次統計を更新しました。"))
