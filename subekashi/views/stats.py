from django.shortcuts import render
from django.utils import timezone
from django.views import View
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    apply_upload_time_filter,
    compute_common_stats,
    get_month_choices,
    get_songrange_availability,
    get_year_choices,
)
from subekashi.models import Song, Stats

SONGRANGE_VALUES = {'all', 'subeana', 'xx'}


class StatsView(View):
    def get(self, request):
        has_subeana, has_xx = get_songrange_availability(Song.objects.all())
        show_all_songrange = has_subeana and has_xx

        songrange = request.GET.get('songrange', 'all')
        if songrange not in SONGRANGE_VALUES:
            songrange = 'all'
        if songrange == 'all' and not show_all_songrange:
            songrange = 'subeana' if has_subeana else 'xx'

        current_year = timezone.now().year
        year_choices = get_year_choices()

        year = request.GET.get('year', 'all')
        if year != 'all' and int(year) not in year_choices:
            year = 'all'

        month_choices = get_month_choices(int(year), current_year) if year != 'all' else list(range(1, 13))
        month = request.GET.get('month', 'all')
        if month != 'all' and int(month) not in month_choices:
            month = 'all'

        qs = apply_songrange_filter(Song.objects.all(), songrange)
        qs = apply_upload_time_filter(qs, year, month)

        stats = compute_common_stats(qs)

        stats_items = [
            {"icon": "fas fa-list-ol", "label": "曲数", "value": stats["song_count"]},
            {"icon": "fas fa-play", "label": "総再生回数", "value": stats["total_view"]},
            {"icon": "far fa-thumbs-up", "label": "総高評価数", "value": stats["total_like"]},
            {"icon": "fas fa-users", "label": "総作者数", "value": stats["total_authors"]},
            {"icon": "fas fa-sitemap", "label": "総模倣曲関係数", "value": stats["total_imitateds"]},
        ]

        monthly_stats = list(Stats.get_monthly_series().values(
            "year", "month", "song_count", "total_view", "total_like",
            "total_authors", "total_imitateds",
        ))

        context = {
            "metatitle": "統計",
            "songrange": songrange,
            "show_all_songrange": show_all_songrange,
            "year": year,
            "month": month,
            "year_choices": year_choices,
            "month_choices": month_choices,
            "stats_items": stats_items,
            "monthly_stats": monthly_stats,
            "description": "すべかしに登録された曲の統計情報。",
        }
        return render(request, "subekashi/stats.html", context)
