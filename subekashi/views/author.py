from django.shortcuts import render
from django.views import View
from subekashi.models import Author, Song


class AuthorView(View):
    def get(self, request, author_id):
        # Author IDで検索、存在しなければ404
        author_obj = Author.get_or_none(author_id)
        if author_obj is None:
            return render(request, 'subekashi/404.html', status=404)
        author_name = author_obj.name

        songInsL = Song.get_for_author(author_id)

        titles = ", ".join(song.title for song in songInsL)
        if len(titles) >= 80:
            titles = titles[:80] + "...など"

        context = {
            "metatitle": author_name,
            "author": author_name,
            "songInsL": songInsL,
            "description": f"{author_name}の曲一覧：{titles}",
        }
        return render(request, "subekashi/author.html", context)
