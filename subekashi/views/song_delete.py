from django.shortcuts import render
from subekashi.models import Song
from subekashi.constants.constants import MAX_ID

def song_delete(request, song_id) :
    try:
        song = Song.objects.get(pk = song_id)
    except:
        return render(request, 'subekashi/404.html', status=404)
    
    dataD = {
        "metatitle" : f"{song_ins.title}の削除申請",
        "song": song_ins
    }
    return render(request, "subekashi/song_delete.html", dataD)