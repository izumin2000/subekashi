from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from config.settings import ROOT_URL
from config.local_settings import ERROR_DISCORD_URL
from subekashi.lib.discord import send_discord
from subekashi.lib.timeline import FIRST_YEAR, TimelineError, get_sheet_title, get_timeline
from subekashi.lib.timeline_import import import_timeline
from collections import Counter
from dataclasses import asdict
import json


class Command(BaseCommand):
    help = "すべあな界隈年表（Googleスプレッドシート）の2018年〜今年のシートを読み取り、曲を登録・更新する。yearオプションを加えることでその年のシートのみを読み取る"

    def handle(self, *args, **options):
        # サーバーOSのタイムゾーン（本番はUTC）によらず、日本時間の今年までを対象にする
        this_year = timezone.localtime(timezone.now()).year
        years = options["year"] or list(range(FIRST_YEAR, this_year + 1))

        try:
            timeline = get_timeline(years)
        except TimelineError as e:
            message = f"{e}。timelineコマンドの処理を打ち切りました"
            self.stderr.write(self.style.ERROR(message))
            send_discord(ERROR_DISCORD_URL, message)
            return

        for year in years:
            if year not in timeline:
                self.stderr.write(self.style.WARNING(f"{get_sheet_title(year)}のシートがありません"))

        if options["json"]:
            rows = [asdict(row) for rows in timeline.values() for row in rows]
            self.stdout.write(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
            return

        for year, rows in timeline.items():
            self.stdout.write(f"{get_sheet_title(year)}：{len(rows)}件")

        rows = [row for rows in timeline.values() for row in rows]
        if options["dry_run"]:
            with transaction.atomic():
                result = import_timeline(rows)
                transaction.set_rollback(True)
        else:
            result = import_timeline(rows)

        self.write_result(result, options["verbosity"], options["dry_run"])

    def write_result(self, result, verbosity, dry_run):
        for song in result.created:
            self.stdout.write(f"{song.title}を新規作成（{ROOT_URL}/songs/{song.id}）")
        for song, history in result.updated:
            self.stdout.write(f"{history.title}（{ROOT_URL}/songs/{song.id}）")
        if verbosity >= 2:
            for row, reason in result.skipped:
                self.stdout.write(f"スキップ：{get_sheet_title(row.year)}{row.row}行目 {row.title}（{reason}）")

        for category, count in Counter(row.category for row in result.unknown_categories).items():
            self.stderr.write(self.style.WARNING(
                f"カテゴリ「{category}」の{count}行は、登録・更新するかが決まっていないためスキップしました"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"{'（dry-run）' if dry_run else ''}新規作成：{len(result.created)}件、更新：{len(result.updated)}件、"
            f"変更なし：{result.unchanged}件、対象外のカテゴリ：{result.excluded}件、スキップ：{len(result.skipped)}件"
        ))
        for reason, count in Counter(reason for _, reason in result.skipped).most_common():
            self.stdout.write(f"  {reason}：{count}件")

    def add_arguments(self, parser):
        parser.add_argument("-y", "--year", nargs="+", type=int, help="読み取る年（複数指定可）")
        parser.add_argument("--json", action="store_true", help="読み取った行をJSONで出力する（曲の登録・更新はしない）")
        parser.add_argument("--dry-run", action="store_true", help="曲の登録・更新の結果を出力するが、DBには保存しない")
