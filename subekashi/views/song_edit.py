from django.shortcuts import render, redirect
from django.utils import timezone
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.ip import *
from subekashi.lib.discord import *


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

    # TODO songビューに
    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        urlForm = request.POST.get("url")
        imitatesForm = request.POST.get("imitates")
        lyricsForm = request.POST.get("lyrics")
        isoriginalForm = request.POST.get("isoriginal")
        isdeletedForm = request.POST.get("isdeleted")
        isjokeForm = request.POST.get("isjoke")
        isinstForm = request.POST.get("isinst")
        issubeanaForm = request.POST.get("issubeana")
        isdraftForm = request.POST.get("isdraft")

        if ("" in [titleForm, channelForm]) :
            return render(request, "subekashi/500.html")
        
        ip = get_ip(request)
        get_id = request.POST.get("id")
        id = int(get_id) if get_id else Song.objects.last().id + 1

        channelForm = channelForm.replace("/", "╱")
        if get_id :
            song_qs = Song.objects.filter(pk = get_id)
            if not song_qs.exists():
                return render(request, 'subekashi/404.html', status=404)
            songIns = song_qs.first()
            songIns.title = titleForm
            songIns.channel = channelForm
        else :
            songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm, defaults={"post_time" : timezone.now()})
        
        oldImitateS = set(songIns.imitate.split(",")) - set([''])
        newImitateS = set(imitatesForm.split(",")) - set([''])

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
        songIns.imitate = imitatesForm

        songIns.lyrics = lyricsForm.replace("\r\n", "\n")
        # TODO urlFormがURL_ICONにあるかのセキュリティチェック
        urls = clean_url(urlForm)
        songIns.url = urls
        songIns.isoriginal = int(bool(isoriginalForm))
        songIns.isjoke = int(bool(isjokeForm))
        songIns.isdeleted = int(bool(isdeletedForm))
        songIns.isinst = int(bool(isinstForm))
        songIns.issubeana = int(bool(issubeanaForm))
        songIns.isdraft = int(bool(isdraftForm))
        songIns.post_time = timezone.now()
        songIns.ip = ip
        songIns.save()
        
                
        content = f'\n\
        {ROOT_URL}/songs/{id}\n\
        タイトル：{titleForm}\n\
        チャンネル : {channelForm}\n\
        URL : {urls}\n\
        ネタ曲 : {"Yes" if isjokeForm else "No"}\n\
        IP : {ip}\n\
        歌詞 : ```{lyricsForm}```'
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
