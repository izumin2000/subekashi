from django.shortcuts import render
from subekashi.models import *
from subekashi.lib.filter import is_lack

def song(request, song_id):
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    # 模倣songリストを取得
    imitate_list = Song.objects.none()
    for imitate_id in song.imitate.split(",") if song.imitate else []:
        imitate_or_none = Song.objects.filter(id = int(imitate_id))
        imitate_list |= imitate_or_none
    
    # 被模倣songリストを取得
    imitated_list = Song.objects.none()
    for imitated_id in song.imitated.split(",") if song.imitated else []:
        imitated_or_none = Song.objects.filter(id = int(imitated_id))
        imitated_list |= imitated_or_none

    # 模倣曲数と被模倣曲数の数をdescriptionに記述
    description = ""
    description += f"模倣曲数：{imitate_list.count()}, " if imitate_list.count() else ""
    description += f"被模倣曲数：{imitated_list.count()}, " if imitated_list.count() else ""
    
    # 歌詞の一部をdescriptionに記述
    descriptio_lyrics = song.lyrics.replace("\r\n", "")[:100]
    description += f"歌詞: {descriptio_lyrics}" if descriptio_lyrics else ""
    
    # テンプレートに渡す辞書を作成
    dataD = {
        "metatitle": f"{song.title} / {song.channel}",
        "song": song,
        "channels": song.channel.split(","),
        "is_lack": is_lack(song),
        "urls": song.url.split(",") if song.url else [],
        "imitated_list": imitated_list,
        "imitate_list": imitate_list,
        "description": description
    }
    return render(request, "subekashi/song.html", dataD)