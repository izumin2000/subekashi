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
        is_original = bool(request.POST.get("is-original-auto", "") + request.POST.get("is-original-manual", ""))
        is_deleted = bool(request.POST.get("is-deleted-auto", "") + request.POST.get("is-deleted-manual", ""))
        is_joke = bool(request.POST.get("is-joke-auto", "") + request.POST.get("is-joke-manual", ""))
        is_inst = bool(request.POST.get("is-inst-auto", "") + request.POST.get("is-inst-manual", ""))
        is_subeana = bool(request.POST.get("is-subeana-auto", "") + request.POST.get("is-subeana-manual", ""))
        
        # YouTube APIから情報取得
        youtube_res = {}
        if is_youtube_url(url) :
            youtube_id = get_youtube_id(url)
            youtube_res = get_youtube_api(youtube_id)
            title = youtube_res.get("title", "")
            channel = youtube_res.get("channel", "")
            
        # URLがYouTubeのURLでない場合はエラー
        if not is_youtube_url(url) and url:
            dataD["error"] = "URLがYouTubeのURLではありません。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # URLが複数ならエラー
        if "," in url:
            dataD["error"] = "URLは複数入力できません。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # 既に登録されているURLの場合はエラー
        cleaned_url = clean_url(url)
        song_qs, _ = song_search({"url": cleaned_url})
        if song_qs.exists() and url:
            dataD["error"] = "URLは既に登録されています。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        # タイトルかチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            dataD["error"] = "タイトルかチャンネルが空です。"
            return render(request, 'subekashi/song_new.html', dataD)
        
        try:
            from subekashi.constants.dynamic.reject import REJECT_LIST
        except:
            REJECT_LIST = []
        
        cleand_title = title.replace(" ,", ",").replace(", ", ",")
        cleand_channel = channel.replace("/", "╱").replace(" ,", ",").replace(", ", ",")
        
        for check_channel in cleand_channel.split(","):
            if check_channel in REJECT_LIST:
                dataD["error"] = f"{check_channel}さんの曲は登録することができません。"
                return render(request, 'subekashi/song_new.html', dataD)
                    
        # TODO cleaned_urlがURL_ICONにあるかのセキュリティチェック
        ip = get_ip(request)
        
        song = Song(
            title = cleand_title,
            channel = cleand_channel,
            url = cleaned_url,
            post_time = timezone.now(),
            isoriginal = is_original,
            isdeleted = is_deleted,
            isjoke = is_joke,
            isinst = is_inst,
            issubeana = is_subeana,
            upload_time = youtube_res.get("upload_time", None),
            view = youtube_res.get("view", None),
            like = youtube_res.get("like", None),
            ip = ip
        )
        
        song.save()
        song_id = song.id
        
        content = f'\n\
        新規作成されました\n\
        {ROOT_URL}/songs/{song_id}\n\
        タイトル：{title}\n\
        チャンネル : {cleand_channel}\n\
        URL : {cleaned_url}\n\
        ネタ曲 : {"Yes" if is_joke else "No"}\n\
        すべあな模倣曲 : {"Yes" if is_subeana else "No"}\n\
        IP : {ip}'
        is_ok = send_discord(NEW_DISCORD_URL, content)
        if not is_ok:
            song.delete()
            return render(request, 'subekashi/500.html', status=500)
        
        return redirect(f'/songs/{song_id}/edit?toast={request.GET.get("toast")}')
    return render(request, 'subekashi/song_new.html', dataD)