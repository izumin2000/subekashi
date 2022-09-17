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
        imitate = request.POST.get("imitate")
        lyrics = request.POST.get("lyrics")

        ins_song = Song.objects.create()
        ins_song.title = title
        ins_song.channel = channel
        if url in "https://www.youtube.com/watch?v=" :
            url = "https://youtu.be/" + url[32:44]
        ins_song.url = url
        ins_song.lyrics = lyrics
        ins_song.save()

    BASE_DIR = str(BASE_DIRpath)
    if "C:" in BASE_DIR :
        dir["basedir"] = "http://127.0.0.1:8000"
    else :
        print("!"*20, "\n", BASE_DIR)
        dir["basedir"] = BASE_DIR
    return render(request, 'subeana/new.html', dir)


def song(request, song_title) :
    dir = {"title" : song_title}
    return render(request, "subeana/song.html", dir)


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer