from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.youtube import *


def song_new(request) :
    dataD = {
        "metatitle": "登録と編集",
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        channel = request.POST.get("channel", "")
        url = request.POST.get("url", "")
        is_orginal = request.POST.get("is-orginal-auto")
        is_deleted = request.POST.get("is-deleted-auto")
        is_joke = request.POST.get("is-joke-auto")
        is_inst = request.POST.get("is-inst-auto")
        is_subeana = request.POST.get("is-subeana-auto")
        
        if is_yt_url(url) :
            yt_id = format_yt_url(url, id=True)
            yt_res = get_youtube_api(yt_id)
            title = yt_res.get("title", "")
            channel = yt_res.get("channel", "")
        
        if ("" in [title, channel]) :
            return render(request, "subekashi/500.html", status=500)
        
        channel_cleand = channel.replace("/", "╱")
        # TODO urlがURL_ICONにあるかのセキュリティチェック
        url = clean_url(url)
        ip = get_ip(request)
        
        song_obj = Song(
            title = title,
            channel = channel_cleand,
            url = url,
            post_time = timezone.now(),
            is_orginal = is_orginal,
            is_deleted = is_deleted,
            is_joke = is_joke,
            is_inst = is_inst,
            is_subeana = is_subeana,
            ip = ip
        )
        song_id = song_obj.id
        
        content = f'\n\
        {ROOT_URL}/songs/{song_id}\n\
        タイトル：{title}\n\
        チャンネル : {channel_cleand}\n\
        URL : {url}\n\
        ネタ曲 : {"Yes" if is_joke else "False"}\n\
        すべあな模倣曲 : {"Yes" if is_subeana else "False"}\n\
        IP : {ip}```'
        is_ok = sendDiscord(NEW_DISCORD_URL, content)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)
        
        song_obj.save()
        
        return redirect(request, 'subekashi/song_edit.html', song_id)
    return render(request, 'subekashi/song_new.html', dataD)