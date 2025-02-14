from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *


def song_new(request) :
    dataD = {
        "metatitle": "登録と編集",
    }

    # TODO songビューに
    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        urlForm = request.POST.get("url")
        
        ip = get_ip(request)
        id = Song.objects.last().id + 1
        
        content = f'\n\
        {ROOT_URL}/songs/{id}\n\
        タイトル：{titleForm}\n\
        チャンネル : {channelForm}\n\
        URL : {urls}\n\
        IP : {ip}```'
        is_ok = sendDiscord(NEW_DISCORD_URL, content)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)
        
        channelForm = channelForm.replace("/", "╱")
        songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm, defaults={"post_time" : timezone.now()})
        
        # TODO urlFormがURL_ICONにあるかのセキュリティチェック
        urls = clean_url(urlForm)
        songIns.url = urls
        songIns.post_time = timezone.now()
        songIns.ip = ip
        songIns.save()
        
        dataD["songIns"] = songIns
        dataD["channels"] = songIns.channel.replace(", ", ",").split(",")
        dataD["urls"] = songIns.url.replace(", ", ",").split(",") if songIns.url else []
        dataD["isExist"] = True
        
        return render(request, 'subekashi/song_edit.html', dataD)
    return render(request, 'subekashi/song_new.html', dataD)