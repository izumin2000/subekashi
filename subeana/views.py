from django.shortcuts import render
from subeana.models import Song
from rest_framework import viewsets
from .serializer import SongSerializer
from config.settings import BASE_DIR as BASE_DIRpath
# Create your views here.
def top(request):
    return render(request, 'subeana/top.html')


def new(request) :
    dir = {}

    if request.method == "POST":
        title = request.POST.get("title")
        channel = request.POST.get("channel")
        url = request.POST.get("url")
        lyrics = request.POST.get("lyrics")
        imitatenums = request.POST.get("imitatenums")

        if ("" in [title, channel, imitatenums]) :
            return render(request, "subeana/error.html")

        ins_song, _ = Song.objects.get_or_create(title = title, defaults = {title : title})
        ins_song.title = title
        ins_song.channel = channel
        if url :
            if url in "https://www.youtube.com/watch?v=" :
                url = "https://youtu.be/" + url[32:44]
                ins_song.url = url
        if lyrics :
            ins_song.lyrics = lyrics

        imitates = set()
        for i in range(int(imitatenums)) :
            imitate = request.POST.get(f"imitate{i + 1}")
            if imitate == "模倣曲模倣" :
                imitate = request.POST.get(f"imitateimitate{i + 1}")
                if imitate :
                    imitates.add(imitate)
            else :
                imitates.add(imitate)

        imitates.discard("模倣曲模倣")
        ins_song.imitate = " ".join(list(imitates))
        ins_song.save()

    BASE_DIR = str(BASE_DIRpath)
    if "C:" in BASE_DIR :
        dir["basedir"] = "http://127.0.0.1:8000"
    else :
        dir["basedir"] = BASE_DIR
    return render(request, 'subeana/new.html', dir)


def song(request, song_title) :
    dir = {"title" : song_title}
    return render(request, "subeana/song.html", dir)

def error(request) :
    return render(request, "subeana/error.html")


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer