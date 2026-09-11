from django.core.management.base import BaseCommand
from django.utils import timezone
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    compute_common_stats,
    month_start,
    next_year_month,
    now_local,
)
from subekashi.models import Song, Stats

SONGRANGES = ["all", "subeana", "xx"]


class Command(BaseCommand):
    help = (
        "月次統計(Stats)の集計・保存。最古のSongの月〜今月までの全期間を再計算する。"
    )

    def handle(self, *args, **options):
        now = now_local()
        current_year, current_month = now.year, now.month

        first_song = Song.objects.exclude(upload_time__isnull=True).order_by('upload_time').first()
        if first_song is None:
            return
        # DBにはUTCで保存されているため、月の境界はローカルタイムゾーンに変換してから判定する
        first_local = timezone.localtime(first_song.upload_time)
        year, month = first_local.year, first_local.month
        while (year, month) <= (current_year, current_month):
            self._recalculate_month(year, month)
            year, month = next_year_month(year, month)

        self.stdout.write(self.style.SUCCESS("月次統計を更新しました。"))

    def _recalculate_month(self, year, month):
        """year年month月分のStatsをsongrange(all/subeana/xx)ごとに再計算・保存する"""
        next_year, next_month = next_year_month(year, month)
        base_qs = Song.objects.filter(upload_time__lt=month_start(next_year, next_month))
        for songrange in SONGRANGES:
            qs = apply_songrange_filter(base_qs, songrange)
            Stats.objects.update_or_create(
                year=year,
                month=month,
                songrange=songrange,
                defaults=compute_common_stats(qs),
            )
