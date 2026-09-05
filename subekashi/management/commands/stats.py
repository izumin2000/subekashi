from django.core.management.base import BaseCommand, CommandError
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
        "月次統計(Stats)の集計・保存。通常は当月分のみを再計算し、--force指定時は"
        "最古のSongの月〜今月までの全期間を再計算する。--year/--monthで任意の1ヶ月のみを"
        "指定して再計算することもできる（過去月をピンポイントで更新したい場合用）"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '-f', '--force',
            action='store_true',
            help='最古のSongの月〜今月までの全期間を再計算する（デプロイ時の過去分バックフィル用）',
        )
        parser.add_argument(
            '--year', type=int, required=False,
            help='--monthと合わせて指定し、その1ヶ月分のみを再計算する',
        )
        parser.add_argument(
            '--month', type=int, required=False,
            help='--yearと合わせて指定し、その1ヶ月分のみを再計算する',
        )

    def handle(self, *args, **options):
        now = now_local()
        current_year, current_month = now.year, now.month

        target_year, target_month = options['year'], options['month']
        if target_year is not None or target_month is not None:
            if target_year is None or target_month is None:
                raise CommandError('--yearと--monthは両方指定してください')
            self._recalculate_month(target_year, target_month)
            self.stdout.write(self.style.SUCCESS(f"{target_year}年{target_month}月分の統計を更新しました。"))
            return

        if options['force']:
            first_song = Song.objects.exclude(upload_time__isnull=True).order_by('upload_time').first()
            if first_song is None:
                return
            # DBにはUTCで保存されているため、月の境界はローカルタイムゾーンに変換してから判定する
            first_local = timezone.localtime(first_song.upload_time)
            year, month = first_local.year, first_local.month
            while (year, month) <= (current_year, current_month):
                self._recalculate_month(year, month)
                year, month = next_year_month(year, month)
        else:
            # 過去月のview/like等は既に確定した値として扱い、当月分のみを再計算する
            # （view/likeは現在値のため当月中は日々伸びうる。過去の全期間を毎回再計算すると
            # データ増加に伴い実行コストが線形以上に増えるため、コードレビュー指摘対応）
            self._recalculate_month(current_year, current_month)

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
