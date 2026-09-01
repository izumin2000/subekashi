from django.shortcuts import render
from django.views import View
from subekashi.lib.kenreki_service import MAX_KEYS, build_keyboard_geometry, compute_kenreki_for_songs
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    apply_upload_time_filter,
    build_stats_items,
    compute_base_stats,
    compute_collaborator_count,
    compute_total_imitates,
    compute_unique_collaborator_count,
    get_view_like_pairs,
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

        # 鍵歴（実績鍵盤）はsongrange/year/monthの絞り込みの影響を受けない、
        # authorの全期間・全曲について、Songごとに算出した鍵歴の総和として算出する
        view_like_pairs = get_view_like_pairs(author_songs)
        kenreki = None
        if view_like_pairs:
            kenreki = compute_kenreki_for_songs(view_like_pairs)
            kenreki["geometry"] = build_keyboard_geometry(min(kenreki["key_count"], MAX_KEYS), kenreki["overflow_color"])

        songrange, show_all_songrange = resolve_songrange(request, author_songs)
        songrange_qs = apply_songrange_filter(author_songs, songrange)
        # 選択肢は対象author自身・選択中のsongrangeで実際に0件にならない年のみに絞る
        year, month, year_choices, month_choices = resolve_year_month(request, songrange_qs)

        qs = apply_upload_time_filter(songrange_qs, year, month)

        stats = compute_base_stats(qs)

        stats_items = build_stats_items(stats, [
            {"icon": "fas fa-list-ol", "label": "曲数", "value": stats["song_count"]},
            {"icon": "fas fa-play", "label": "総再生回数", "value": stats["total_view"]},
            {"icon": "far fa-thumbs-up", "label": "総高評価数", "value": stats["total_like"]},
            {"icon": "fas fa-users", "label": "合作人数(重複あり)", "value": compute_collaborator_count(qs, author_id)},
            {"icon": "fas fa-user-friends", "label": "合作人数(重複なし)", "value": compute_unique_collaborator_count(qs, author_id)},
            {"icon": "fas fa-sitemap imitate", "label": "総模倣元関係数", "value": compute_total_imitates(qs)},
            {"icon": "fas fa-sitemap", "label": "総模倣曲関係数", "value": stats["total_imitateds"]},
        ])

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
            "kenreki": kenreki,
            "description": f"{author_name}の統計情報。",
        }
        return render(request, "subekashi/author_stats.html", context)
