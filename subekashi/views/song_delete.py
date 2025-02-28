from django.shortcuts import render
from subekashi.models import Song
from subekashi.constants.constants import MAX_ID

def song_delete(request, song_id) :
    if song_id < 0 or song_id > MAX_ID :
        return render(request, 'subekashi/404.html', status=404)
        
    song_qs = Song.objects.filter(pk = song_id)
    if not song_qs.exists() :
        return render(request, 'subekashi/404.html', status=404)
    
    song_ins = song_qs.first()
    dataD = {
        "metatitle" : f"{song_ins.title}の削除申請",
        "song": song_ins
    }
    return render(request, "subekashi/song_delete.html", dataD)