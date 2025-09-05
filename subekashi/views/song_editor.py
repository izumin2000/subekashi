from django.shortcuts import render
from subekashi.models import *

def song_editor(request, song_id):
    # Songがなければ404
    try :
        song = Song.objects.get(pk = song_id)
    except :
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {
        "metatitle": f"{song.title}の編集履歴",
        "song": song,
    }
    
    return render(request, 'subekashi/song_editor.html', dataD)