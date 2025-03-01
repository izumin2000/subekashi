from django.shortcuts import render, redirect
from subekashi.models import Song
from subekashi.lib.ip import *
from subekashi.lib.discord import *

def song_delete(request, song_id) :
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {
        "metatitle" : f"{song.title}の削除申請",
        "song": song
    }
    
    if request.method == "POST":
        reason = request.POST.get("reason", "")
        
        # もし削除理由を入力していないのなら
        if not reason:
            dataD["result"] = "invalid"
            return render(request, "subekashi/song_delete.html", dataD)
        
        # Discordに送信
        content = f' \
        ```{song.id}``` \n\
        {ROOT_URL}/songs/{song.id} \n\
        タイトル：{song.title}\n\
        チャンネル名：{song.channel}\n\
        理由：{reason}\n\
        IP：{get_ip(request)}\
        '
        is_ok = send_discord(DELETE_DISCORD_URL, content)
        if not is_ok:
            dataD["result"] = "error"
            return render(request, 'subekashi/song_delete.html', dataD)
        
        return redirect(f'/songs/{song_id}?toast=delete')
        
    return render(request, "subekashi/song_delete.html", dataD)