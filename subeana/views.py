from django.shortcuts import render
from subeana.models import Song
from rest_framework import viewsets
from .serializer import SongSerializer
from config.settings import BASE_DIR as BASE_DIRpath
import hashlib
import requests

# パスワード関連
SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"


def get_API(url) :
    try :
        get = requests.get(url)
    except :        # プロキシエラー等のエラーが発生したら
        print("5xx Error")
        return ""

    if (get.status_code == 200) :
        try :
            get_dict = get.json()
        except :        # JSON形式ではなかったら（メンテナンス等）
            print("Not JSON Error", get.status_code)
            return ""

        if "error" in get_dict :     # dictのキーにerrorがあったら
            print("Invalid path Error", get.status_code)
            return ""
        
        if "message" in get_dict :     # dictのキーにerrorがあったら
            print("404 on json API", get.status_code)
            
        else :      # 正常に取得できたら
            print("OK", get.status_code)
            return get_dict

    else :      # エラーステータスコードを受け取ったら（HEROKU error等）
        print("not 2xx", get.status_code)
        return ""


def top(request):
    return render(request, 'subeana/top.html')


def new(request) :
    dir = {}

    if request.method == "POST":
        inp_title = request.POST.get("title")
        inp_channel = request.POST.get("channel")
        inp_url = request.POST.get("url")
        inp_lyrics = request.POST.get("lyrics")
        inp_imitatenums = request.POST.get("imitatenums")

        if ("" in [inp_title, inp_channel, inp_imitatenums]) :
            return render(request, "subeana/error.html")

        ins_song, _ = Song.objects.get_or_create(title = inp_title, defaults = {"title" : inp_title})
        ins_song.title = inp_title
        ins_song.channel = inp_channel
        if inp_url :
            if inp_url in "https://www.youtube.com/watch?v=" :
                url = "https://youtu.be/" + inp_url[32:44]
                ins_song.url = url
            else :
                ins_song.url = inp_url
        if inp_lyrics :
            ins_song.lyrics = inp_lyrics

        imitates = set()
        for i in range(int(inp_imitatenums)) :
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


def dev(request) :

    return render(request, "subeana/dev.html")


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer