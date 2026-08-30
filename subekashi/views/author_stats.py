from django.shortcuts import render
from django.views import View
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    apply_upload_time_filter,
    compute_collaborator_count,
    compute_common_stats,
    compute_total_imitates,
    compute_unique_collaborator_count,
    get_song_ids,
    resolve_songrange,
    resolve_year_month,
)
from subekashi.models import Author, Song


class AuthorStatsView(View):
    def get(self, request, author_id):
        author_obj = Author.get_or_none(author_id)
        if author_obj is None:
            return render(request, 'subekashi/404.html', status=404)
        author_name = author_obj.name

        author_songs = Song.objects.filter(authors__id=author_id).distinct()
        songrange, show_all_songrange = resolve_songrange(request, author_songs)
        year, month, year_choices, month_choices = resolve_year_month(request)

        qs = apply_songrange_filter(author_songs, songrange)
        qs = apply_upload_time_filter(qs, year, month)
        song_ids = get_song_ids(qs)

        stats = compute_common_stats(song_ids)

        stats_items = [
            {"icon": "fas fa-list-ol", "label": "曲数", "value": stats["song_count"]},
            {"icon": "fas fa-play", "label": "総再生回数", "value": stats["total_view"]},
            {"icon": "far fa-thumbs-up", "label": "総高評価数", "value": stats["total_like"]},
            {"icon": "fas fa-users", "label": "合作人数(重複あり)", "value": compute_collaborator_count(song_ids, author_id)},
            {"icon": "fas fa-user-friends", "label": "合作人数(重複なし)", "value": compute_unique_collaborator_count(song_ids, author_id)},
            {"icon": "fas fa-sitemap imitate", "label": "総模倣元関係数", "value": compute_total_imitates(song_ids)},
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
