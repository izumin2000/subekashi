from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.filter import islack


def song(request, songId) :
    # TODO リファクタリング
    songIns = Song.objects.filter(pk = songId)
    isExist = bool(songIns)
    dataD = {
        "isExist" : isExist,
        "islack" : bool(songIns.filter(islack))
    }

    if isExist :
        songIns = songIns.first()
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
    else :
        return render(request, 'subekashi/404.html', status=404)