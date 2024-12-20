from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *


def delete(request) :
    dataD = {
        "metatitle" : "削除申請",
    }
    dataD["isDeleted"] = True
    dataD["songInsL"] = Song.objects.all()
    
    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        songIns = Song.objects.filter(title = titleForm, channel = channelForm)
        if not songIns :
            return render(request, 'subekashi/500.html')
        songIns = songIns.first()
        reasonForm = request.POST.get("reason")
        content = f' \
        ```{songIns.id}``` \n\
        {ROOT_URL}/songs/{songIns.id} \n\
        タイトル：{songIns.title}\n\
        チャンネル名：{songIns.channel}\n\
        理由：{reasonForm}\n\
        IP：{get_ip(request)}\
        '
        is_ok = sendDiscord(DELETE_DISCORD_URL, content)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)
        
    return render(request, 'subekashi/song.html', dataD)