from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.filter import islack
from subekashi.constants.constants import MAX_ID
from subekashi.lib.ip import *
from subekashi.lib.discord import *


def song(request, song_id) :
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    songIns = song_qs.first()
    dataD = {
        "islack" : song_qs.filter(islack).exists()
    }
    
    reason = request.POST.get("reason")
    if reason :
        content = f' \
        ```{songIns.id}``` \n\
        {ROOT_URL}/songs/{songIns.id} \n\
        タイトル：{songIns.title}\n\
        チャンネル名：{songIns.channel}\n\
        理由：{reason}\n\
        IP：{get_ip(request)}\
        '
        is_ok = send_discord(DELETE_DISCORD_URL, content)
        if not is_ok:
            # TODO これもtoastを表示
            return render(request, 'subekashi/500.html', status=500)
        
        dataD["toast_type"] = "ok"
        dataD["toast_text"] = f"{songIns.title}の削除申請を送信しました。"

    # TODO リファクタリング
    dataD["metatitle"] = f"{songIns.title} / {songIns.channel}" if songIns else "全て削除の所為です。"
    dataD["songIns"] = songIns
    dataD["channels"] = songIns.channel.replace(", ", ",").split(",")
    dataD["urls"] = songIns.url.replace(", ", ",").split(",") if songIns.url else []
    description = ""
    jokerange = request.COOKIES.get("jokerange", "off")
    if songIns.imitate :
        imitateInsL = []
        imitates = songIns.imitate.split(",")
        for imitateId in imitates:
            imitateInsQ = Song.objects.filter(id = int(imitateId))
            if imitateInsQ :
                imitateIns = imitateInsQ.first()
                if imitateIns.isjoke and (jokerange == "off") :
                    continue
                imitateInsL.append(imitateIns)

        dataD["imitateInsL"] = imitateInsL
        description += f"模倣曲数：{len(imitateInsL)}, "

    if songIns.imitated :
        imitatedInsL = []
        imitateds = set(songIns.imitated.split(",")) - set([""])
        for imitatedId in imitateds :
            imitatedInsQ = Song.objects.filter(id = int(imitatedId))
            if imitatedInsQ :
                imitatedIns = imitatedInsQ.first()
                if imitatedIns.isjoke and (jokerange == "off") :
                    continue
                imitatedInsL.append(imitatedIns)

        dataD["imitatedInsL"] = imitatedInsL
        description += f"被模倣曲数：{len(imitatedInsL)}, "
    lyrics = songIns.lyrics[:min(100, len(songIns.lyrics))]
    lyrics = lyrics.replace("\r\n", "")
    description += f"歌詞: {lyrics}" if lyrics else ""
    dataD["description"] = description
    return render(request, "subekashi/song.html", dataD)