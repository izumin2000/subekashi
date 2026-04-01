from django.shortcuts import render
from subekashi.models import Author, Song


def author(request, author_id):
    # Author IDで検索、存在しなければ404
    author_obj = Author.get_or_none(author_id)
    if author_obj is None:
        return render(request, 'subekashi/404.html', status=404)
    author_name = author_obj.name

    dataD = {
        "metatitle": author_name,
        "author": author_name,
    }

    songInsL = Song.get_for_author(author_id)

    dataD["songInsL"] = songInsL
    titles = ", ".join(song.title for song in songInsL)
    if len(titles) >= 80:
        titles = titles[:80] + "...など"
    dataD["description"] = f"{author_name}の曲一覧：{titles}"
    return render(request, "subekashi/author.html", dataD)
