from django.shortcuts import render, get_object_or_404
from subekashi.models import *


def author(request, author_id):
    # Author IDで検索、存在しなければ404
    author_obj = get_object_or_404(Author, id=author_id)
    author_name = author_obj.name

    dataD = {
        "metatitle": author_name,
    }
    dataD["channel"] = author_name

    # authorsフィールドでフィルタ
    songInsL = Song.objects.filter(authors__id=author_id).prefetch_related('authors').distinct()

    dataD["songInsL"] = songInsL
    titles = ", ".join([songIns.title for songIns in songInsL[::-1]])
    if len(titles) >= 80:
        titles = titles[:80] + "...など"
    dataD["description"] = f"{author_name}の曲一覧：{titles}"
    return render(request, "subekashi/channel.html", dataD)
