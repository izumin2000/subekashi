from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.filter import islack


def song(request, song_id) :
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {
        "metatitle": f"{song.title} / {song.channel}",
        "song": song,
        "channels": song.channel.split(","),
        "islack": islack.check(song.__dict__)
    }
    
    dataD["urls"] = song.url.split(",") if song.url else []
    description = ""
    jokerange = request.COOKIES.get("jokerange", "off")
    if song.imitate :
        imitateInsL = []
        imitates = song.imitate.split(",")
        for imitateId in imitates:
            imitateInsQ = Song.objects.filter(id = int(imitateId))
            if imitateInsQ :
                imitateIns = imitateInsQ.first()
                if imitateIns.isjoke and (jokerange == "off") :
                    continue
                imitateInsL.append(imitateIns)

        dataD["imitateInsL"] = imitateInsL
        description += f"模倣曲数：{len(imitateInsL)}, "

    if song.imitated :
        imitatedInsL = []
        imitateds = set(song.imitated.split(",")) - set([""])
        for imitatedId in imitateds :
            imitatedInsQ = Song.objects.filter(id = int(imitatedId))
            if imitatedInsQ :
                imitatedIns = imitatedInsQ.first()
                if imitatedIns.isjoke and (jokerange == "off") :
                    continue
                imitatedInsL.append(imitatedIns)

        dataD["imitatedInsL"] = imitatedInsL
        description += f"被模倣曲数：{len(imitatedInsL)}, "
    lyrics = song.lyrics[:min(100, len(song.lyrics))]
    lyrics = lyrics.replace("\r\n", "")
    description += f"歌詞: {lyrics}" if lyrics else ""
    dataD["description"] = description
    return render(request, "subekashi/song.html", dataD)