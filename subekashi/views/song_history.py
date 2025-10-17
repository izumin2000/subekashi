from django.shortcuts import render
from subekashi.models import *

def song_history(request, song_id):
    # Songがなければ404
    try :
        song = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {
        "metatitle": f"{song.title}の編集履歴",
        "song": song,
        "historys": History.objects.filter(song = song).order_by("-edited_time")
    }
    
    return render(request, 'subekashi/song_history.html', dataD)