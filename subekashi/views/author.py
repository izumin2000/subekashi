from django.shortcuts import render
from django.views import View
from subekashi.lib.kenreki_service import compute_kenreki_for_songs
from subekashi.lib.stats_service import get_view_like_pairs
from subekashi.models import Author, Song


class AuthorView(View):
    def get(self, request, author_id):
        # Author IDで検索、存在しなければ404
        author_obj = Author.get_or_none(author_id)
        if author_obj is None:
            return render(request, 'subekashi/404.html', status=404)
        author_name = author_obj.name

        songInsL = Song.get_for_author(author_id)

        titles = ", ".join(songInsL.values_list('title', flat=True))
        if len(titles) >= 80:
            titles = titles[:80] + "...など"

        view_like_pairs = get_view_like_pairs(songInsL)
        kenreki = None
        if view_like_pairs:
            kenreki = compute_kenreki_for_songs(view_like_pairs)

        context = {
            "metatitle": author_name,
            "author": author_name,
            "author_id": author_obj.id,
            "songInsL": songInsL,
            "alias_count": len(author_obj.get_transitive_aliases()),
            "kenreki": kenreki,
            "description": f"{author_name}の曲一覧：{titles}",
        }
        return render(request, "subekashi/author.html", context)
