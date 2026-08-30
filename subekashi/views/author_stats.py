from django.shortcuts import render
from django.utils import timezone
from django.views import View
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    apply_upload_time_filter,
    compute_collaborator_count,
    compute_common_stats,
    compute_total_imitates,
    compute_unique_collaborator_count,
    get_month_choices,
    get_songrange_availability,
    get_year_choices,
    parse_int_or_none,
)
from subekashi.models import Author, Song

SONGRANGE_VALUES = {'all', 'subeana', 'xx'}


class AuthorStatsView(View):
    def get(self, request, author_id):
        author_obj = Author.get_or_none(author_id)
        if author_obj is None:
            return render(request, 'subekashi/404.html', status=404)
        author_name = author_obj.name

        author_songs = Song.objects.filter(authors__id=author_id).distinct()
        has_subeana, has_xx = get_songrange_availability(author_songs)
        show_all_songrange = has_subeana and has_xx

        songrange = request.GET.get('songrange', 'all')
        if songrange not in SONGRANGE_VALUES:
            songrange = 'all'
        if songrange == 'all' and not show_all_songrange:
            songrange = 'subeana' if has_subeana else 'xx'

        current_year = timezone.now().year
        year_choices = get_year_choices()

        year = request.GET.get('year', 'all')
        if year != 'all' and parse_int_or_none(year) not in year_choices:
            year = 'all'

        month_choices = get_month_choices(int(year), current_year) if year != 'all' else list(range(1, 13))
        month = request.GET.get('month', 'all')
        if month != 'all' and parse_int_or_none(month) not in month_choices:
            month = 'all'

        qs = apply_songrange_filter(author_songs, songrange)
        qs = apply_upload_time_filter(qs, year, month)

        stats = compute_common_stats(qs)

        stats_items = [
            {"icon": "fas fa-list-ol", "label": "曲数", "value": stats["song_count"]},
            {"icon": "fas fa-play", "label": "総再生回数", "value": stats["total_view"]},
            {"icon": "far fa-thumbs-up", "label": "総高評価数", "value": stats["total_like"]},
            {"icon": "fas fa-users", "label": "合作人数(重複あり)", "value": compute_collaborator_count(qs, author_id)},
            {"icon": "fas fa-user-friends", "label": "合作人数(重複なし)", "value": compute_unique_collaborator_count(qs, author_id)},
            {"icon": "fas fa-sitemap imitate", "label": "総模倣元関係数", "value": compute_total_imitates(qs)},
            {"icon": "fas fa-sitemap", "label": "総模倣曲関係数", "value": stats["total_imitateds"]},
        ]

        context = {
            "metatitle": f"{author_name}の統計",
            "author": author_name,
            "author_id": author_obj.id,
            "songrange": songrange,
            "show_all_songrange": show_all_songrange,
            "year": year,
            "month": month,
            "year_choices": year_choices,
            "month_choices": month_choices,
            "stats_items": stats_items,
            "description": f"{author_name}の統計情報。",
        }
        return render(request, "subekashi/author_stats.html", context)
