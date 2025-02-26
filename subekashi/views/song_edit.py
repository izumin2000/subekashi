from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *
from subekashi.lib.search import song_search


def song_edit(request, song_id) :
    try :
        song_obj = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    MAX_META_TITLE = 25
    metatitle = f"{song_obj.title}の編集" if len(song_obj.title) < MAX_META_TITLE else f"{song_obj.title[:MAX_META_TITLE]}...の編集"
    dataD = {
        "metatitle": metatitle,
        "song": song_obj,
    }

    if request.method == "POST":
        title = request.POST.get("title", "")
        channel = request.POST.get("channel", "")
        url = request.POST.get("url", "")
        imitates = request.POST.get("imitates", "")
        lyrics = request.POST.get("lyrics", "")
        is_original = bool(request.POST.get("is-original"))
        is_deleted = bool(request.POST.get("is-deleted"))
        is_joke = bool(request.POST.get("is-joke"))
        is_inst = bool(request.POST.get("is-inst"))
        is_subeana = bool(request.POST.get("is-subeana"))
        is_draft = bool(request.POST.get("is-draft"))
        
        # 既に登録されているURLの場合はエラー
        cleaned_url = clean_url(url)
        cleaned_url_list = cleaned_url.split(",")
        for cleaned_url_item in cleaned_url_list:
            song_qs, _ = song_search({"url": cleaned_url_item})
            if song_qs.exists() and url:
                return render(request, "subekashi/500.html", status=500)
        
        # タイトルとチャンネルが空の場合はエラー
        if ("" in [title, channel]) :
            return render(request, "subekashi/500.html", status=500)
        
        # 模倣関係以外のsong_objの更新
        ip = get_ip(request)
        cleand_channel = channel.replace("/", "╱")
        song_obj.update(
            title = title,
            channel = cleand_channel,
            url = cleaned_url,
            post_time = timezone.now(),
            isoriginal = is_original,
            isdeleted = is_deleted,
            isjoke = is_joke,
            isinst = is_inst,
            issubeana = is_subeana,
            ip = ip
        )

        

        
        old_imitate_list = song_obj.imitate.split(",")
        oldImitateS = set(old_imitate_list) - set([''])
        newImitateS = set(imitates.split(",")) - set([''])

        appendImitateS = newImitateS - oldImitateS
        deleteImitateS = oldImitateS - newImitateS

        for imitateId in appendImitateS :
            imitatedIns = Song.objects.get(pk = imitateId)
            imitatedInsL = set(imitatedIns.imitated.split(","))
            imitatedInsL.add(str(songIns.id))
            imitatedIns.imitated = ",".join(imitatedInsL)
            imitatedIns.post_time = timezone.now()
            imitatedIns.save()
        for imitateId in deleteImitateS :
            imitatedIns = Song.objects.get(pk = imitateId)
            imitatedInsL = set(imitatedIns.imitated.split(","))
            imitatedInsL.remove(str(songIns.id))
            imitatedIns.imitated = ",".join(imitatedInsL)
            imitatedIns.post_time = timezone.now()
            imitatedIns.save()
        songIns.imitate = imitates

        songIns.lyrics = lyrics.replace("\r\n", "\n")
        # TODO urlがURL_ICONにあるかのセキュリティチェック
        urls = clean_url(url)
        songIns.url = urls
        songIns.isoriginal = int(bool(is_original))
        songIns.isjoke = int(bool(is_joke))
        songIns.isdeleted = int(bool(is_deleted))
        songIns.isinst = int(bool(is_inst))
        songIns.issubeana = int(bool(is_subeana))
        songIns.isdraft = int(bool(is_draft))
        songIns.post_time = timezone.now()
        songIns.ip = ip
        songIns.save()
        
                
        content = f'\n\
        {ROOT_URL}/songs/{id}\n\
        タイトル：{title}\n\
        チャンネル : {channel}\n\
        URL : {urls}\n\
        ネタ曲 : {"Yes" if is_joke else "No"}\n\
        IP : {ip}\n\
        歌詞 : ```{lyrics}```'
        is_ok = sendDiscord(NEW_DISCORD_URL, content)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)
        
        imitateInsL = []
        if songIns.imitate :
            imitateInsL = list(map(lambda i : Song.objects.get(pk = int(i)), songIns.imitate.split(",")))
            dataD["imitateInsL"] = imitateInsL
        dataD["songIns"] = songIns
        dataD["channels"] = songIns.channel.replace(", ", ",").split(",")
        dataD["urls"] = songIns.url.replace(", ", ",").split(",") if songIns.url else []
        dataD["isExist"] = True
        
        return redirect(f'/songs/{songIns.id}')
    return render(request, 'subekashi/song_edit.html', dataD)
