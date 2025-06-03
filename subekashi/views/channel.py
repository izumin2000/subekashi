from django.shortcuts import render
from django.views.decorators.cache import never_cache
from subekashi.models import *


@never_cache
def channel(request, channelName) :
    dataD = {
        "metatitle" : channelName,
    }
    dataD["channel"] = channelName
    songInsL = []
    for songIns in Song.objects.all() :
        if channelName in songIns.channel.split(",") :
            songInsL.append(songIns)
    dataD["songInsL"] = songInsL
    titles = ", ".join([songIns.title for songIns in songInsL[::-1]])
    if len(titles) >= 80:
        titles = titles[:80] + "...など"
    dataD["description"] = f"{channelName}の曲一覧：{titles}"
    return render(request, "subekashi/channel.html", dataD)