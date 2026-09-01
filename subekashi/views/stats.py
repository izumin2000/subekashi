from django.shortcuts import render
from django.views import View
from subekashi.lib.kenreki_service import compute_kenreki_for_songs
from subekashi.lib.stats_service import (
    apply_songrange_filter,
    apply_upload_time_filter,
    build_stats_items,
    compute_common_stats,
    filter_monthly_series_by_year_month,
    get_view_like_pairs,
    resolve_songrange,
    resolve_year_month,
    with_monthly_deltas,
)
from subekashi.models import Song, Stats


class StatsView(View):
    def get(self, request):
        songrange, show_all_songrange = resolve_songrange(request, Song.objects.all())
        songrange_qs = apply_songrange_filter(Song.objects.all(), songrange)
        # 選択中のsongrangeでは0件になる年は選択肢に出さない
        year, month, year_choices, month_choices = resolve_year_month(request, songrange_qs)

        qs = apply_upload_time_filter(songrange_qs, year, month)

        stats = compute_common_stats(qs)

        stats_items = build_stats_items(stats, [
            {"icon": "fas fa-list-ol", "label": "曲数", "value": stats["song_count"]},
            {"icon": "fas fa-play", "label": "総再生回数", "value": stats["total_view"]},
            {"icon": "far fa-thumbs-up", "label": "総高評価数", "value": stats["total_like"]},
            {"icon": "fas fa-users", "label": "総作者数", "value": stats["total_authors"]},
            {"icon": "fas fa-sitemap", "label": "総模倣曲関係数", "value": stats["total_imitateds"]},
        ])

        # 鍵歴はここでは他の統計項目と同様、絞り込みに連動したstat-itemとしてのみ表示する
        # （鍵盤ビジュアルは無し、値の着色も無し）。Songごとに算出した鍵歴の総和として算出する
        kenreki = None
        if stats["song_count"] > 0:
            kenreki = compute_kenreki_for_songs(get_view_like_pairs(qs))
            kenreki["overflow_color"] = None

        monthly_series = list(Stats.get_monthly_series(songrange).values(
            "year", "month", "song_count", "total_view", "total_like",
            "total_authors", "total_imitateds",
        ))
        # 差分(月ごとモード用)は絞り込み前の全期間から計算してから、表示範囲をyear/monthで絞り込む
        monthly_stats = filter_monthly_series_by_year_month(with_monthly_deltas(monthly_series), year, month)

        context = {
            "metatitle": "統計",
            "songrange": songrange,
            "show_all_songrange": show_all_songrange,
            "year": year,
            "month": month,
            "year_choices": year_choices,
            "month_choices": month_choices,
            "stats_items": stats_items,
            "kenreki": kenreki,
            "monthly_stats": monthly_stats,
            "description": "すべかしに登録された曲の統計情報。",
        }
        return render(request, "subekashi/stats.html", context)
