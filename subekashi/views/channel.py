from django.shortcuts import render
from subekashi.models import *


def channel(request, channelName) :
    dataD = {
        "metatitle" : channelName,
    }
    dataD["channel"] = channelName

    # authorsフィールドでフィルタ
    songInsL = Song.objects.filter(authors__name=channelName).distinct()

    dataD["songInsL"] = songInsL
    titles = ", ".join([songIns.title for songIns in songInsL[::-1]])
    if len(titles) >= 80:
        titles = titles[:80] + "...など"
    dataD["description"] = f"{channelName}の曲一覧：{titles}"
    return render(request, "subekashi/channel.html", dataD)