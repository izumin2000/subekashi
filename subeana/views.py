from django.shortcuts import render
from subeana.models import Song
from rest_framework import viewsets
from .serializer import SongSerializer
# Create your views here.
def top(request):
    return render(request, 'subeana/top.html')


def new(request) :
    if request.method == "POST":
        title = request.POST.get("title")
        channel = request.POST.get("channel")
        url = request.POST.get("url")
        imitate = request.POST.get("imitate")
        lyrics = request.POST.get("lyrics")

        ins_song = Song.objects.create()
        ins_song.title = title
        # ins_song.channel = channel
        ins_song.url = url
        ins_song.lyrics = lyrics
        ins_song.save()
    return render(request, 'subeana/new.html')


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer