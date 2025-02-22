from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.youtube import *
from subekashi.lib.search import song_search


def song_new(request) :
    dataD = {
        "metatitle": "曲の登録",
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        channel = request.POST.get("channel", "")
        url = request.POST.get("url", "")
        is_original = bool(request.POST.get("is-original-auto"))
        is_deleted = bool(request.POST.get("is-deleted-auto"))
        is_joke = bool(request.POST.get("is-joke-auto"))
        is_inst = bool(request.POST.get("is-inst-auto"))
        is_subeana = bool(request.POST.get("is-subeana-auto"))
        
        # YouTube APIから情報取得
        yt_res = {}
        if is_yt_url(url) :
            yt_id = format_yt_url(url, id=True)
            yt_res = get_youtube_api(yt_id)
            title = yt_res.get("title", "")
            channel = yt_res.get("channel", "")
            
        # URLがYouTubeのURLでない場合はエラー
        if not is_yt_url(url) and url:
            return render(request, "subekashi/500.html", status=500)
        
        # URLが複数ならエラー
        if "," in url:
            return render(request, "subekashi/500.html", status=500)
        
        # 既に登録されているURLの場合はエラー
        cleaned_url = clean_url(url)
        song_qs, _ = song_search({"url": cleaned_url})
        if song_qs.exists() and url:
            return render(request, "subekashi/500.html", status=500)
        
        # タイトルとチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            return render(request, "subekashi/500.html", status=500)
        
        cleand_channel = channel.replace("/", "╱")
        # TODO cleaned_urlがURL_ICONにあるかのセキュリティチェック
        ip = get_ip(request)
        
        song_obj = Song(
            title = title,
            channel = cleand_channel,
            url = cleaned_url,
            post_time = timezone.now(),
            isoriginal = is_original,
            isdeleted = is_deleted,
            isjoke = is_joke,
            isinst = is_inst,
            issubeana = is_subeana,
            upload_time = yt_res.get("upload_time", None),
            view = yt_res.get("view", None),
            like = yt_res.get("like", None),
            ip = ip
        )
        
        song_obj.save()
        song_id = song_obj.id
        
        content = f'\n\
        新規作成されました\n\
        {ROOT_URL}/songs/{song_id}\n\
        タイトル：{title}\n\
        チャンネル : {cleand_channel}\n\
        URL : {cleaned_url}\n\
        ネタ曲 : {"Yes" if is_joke else "False"}\n\
        すべあな模倣曲 : {"Yes" if is_subeana else "False"}\n\
        IP : {ip}```'
        is_ok = sendDiscord(NEW_DISCORD_URL, content)
        if not is_ok:
            song_obj.delete()
            return render(request, 'subekashi/500.html', status=500)
        
        return redirect(f'/songs/{song_id}/edit')
    return render(request, 'subekashi/song_new.html', dataD)