from django.shortcuts import render
from subeana.models import Song, Ai
from rest_framework import viewsets
from .serializer import SongSerializer, AiSerializer
from config.settings import BASE_DIR as BASE_DIRpath
import hashlib
import requests
from time import sleep
from .reset import SUBEANA_LIST
import random
from janome.tokenizer import Tokenizer
import networkx as nx
import random
import re

# パスワード関連
SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"
REPLACEBLE_HINSHIS = ["名詞", "動詞"]


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


def get_basedir() :
    BASE_DIR = str(BASE_DIRpath)
    if "C:" in BASE_DIR :
        return "http://127.0.0.1:8000"
    elif "app" in BASE_DIR :
        return ""


def counter(word) :
    word = str(word)
    hiragana = [(i >= "ぁ") and (i <= "ゟ") for i in word].count(True)
    katakana = [(i >= "ァ") and (i <= "ヿ") for i in word].count(True)
    kanji = [(i >= "一") and (i <= "鿼") for i in word].count(True)
    return hiragana, katakana, kanji


def tokenizer_janome(text):
    toklist = []
    j_t = Tokenizer()

    for tok in j_t.tokenize(text, wakati=False) :
        hinshi = tok.part_of_speech.split(',')[0]
        if hinshi == "動詞" :
            katsuyou = tok.infl_form[:2]
        elif hinshi == "形容詞" :
            katsuyou = tok.infl_form[:2]
        elif hinshi == "名詞" :
            katsuyou = tok.part_of_speech
        else :
            katsuyou = ""
        toklist.append((tok.surface, hinshi, katsuyou))
    return toklist

def vector_generate(ins_original, ins_imitates) :
    lyrics = ""
    simD = {}
    tok = tokenizer_janome(ins_original.lyrics)    
    for ins_imitate in ins_imitates :
        ruigo = ins_imitate.ruigo
        if ruigo :
            for hinshi, words in eval(ruigo).items() :
                if hinshi in simD.keys() :
                    simD[hinshi] += words
                else :
                    simD[hinshi] = words

    before_hinshi = ""
    for word, hinshi, katsuyou in tok :
        if (hinshi in REPLACEBLE_HINSHIS) and not(word.isdigit()) :
            if (hinshi == "名詞") and (before_hinshi == "名詞") :
                lyrics += word
                continue
            before_hinshi = hinshi
            if (hinshi + katsuyou) in simD.keys() :
                fitL = [word]
                for sim in simD[hinshi + katsuyou] :
                    if (counter(word) == counter(sim)) :
                        fitL.append(sim)
                lyrics += random.choice(fitL)
            else :
                lyrics += word
            # simD[hinshi + katsuyou].remove(sim)
        else :
            lyrics += word

        before_hinshi = hinshi
    ais_ins = []
    for lyric in lyrics.split("\n") :
        if len(lyric) >= 2 :
            ai_ins = Ai.objects.create()
            ai_ins.lyrics = lyric
            ai_ins.save()
            ais_ins.append(ai_ins)
    return ais_ins


def format_url(url) :
    if "https://www.youtube.com/watch" in url :
        return "https://youtu.be/" + url[32:43]
    else :
        return url


def top(request):
    dir = {}
    ins_songs = Song.objects.exclude(lyrics = "")[5::-1]
    dir["ins_songs"] = ins_songs
    ins_lacks = list(Song.objects.filter(lyrics = "").exclude(channel = "")) + list(Song.objects.filter(url = "").exclude(channel = ""))
    if ins_lacks :
        ins_lacks = random.sample(ins_lacks, min(6, len(ins_lacks)))
        dir["ins_lacks"] = ins_lacks
    ins_nones = list(Song.objects.filter(channel = ""))
    if ins_nones :
        ins_nones = random.sample(ins_nones, min(6, len(ins_nones)))
        dir["ins_nones"] = ins_nones
    dir["basedir"] = get_basedir()
    return render(request, 'subeana/top.html', dir)


def new(request) :
    dir = {}

    if request.method == "POST":
        inp_title = request.POST.get("title")
        inp_channel = request.POST.get("channel")
        inp_url = request.POST.get("url")
        inp_lyrics = request.POST.get("lyrics")
        inp_imitatenums = request.POST.get("imitatenums")
        inp_isjapanese = request.POST.get("isjapanese")
        inp_isjoke = request.POST.get("isjoke")

        if ("" in [inp_title, inp_channel, inp_imitatenums]) :
            return render(request, "subeana/error.html")

        ins_song, iscreated = Song.objects.get_or_create(title = inp_title, defaults = {"title" : inp_title})

        ins_song.title = inp_title
        if iscreated or not(iscreated or ins_song.channel) :
            ins_song.channel = inp_channel
        ins_song.isjapanese = bool(inp_isjapanese)
        ins_song.isjoke = bool(inp_isjoke)

        if inp_url and (iscreated or not(iscreated or ins_song.url)):
            ins_song.url = format_url(inp_url)
        if inp_lyrics and (iscreated or not(iscreated or ins_song.lyrics)) :
            ins_song.lyrics = inp_lyrics

        imitates = set()
        for i in range(int(inp_imitatenums)) :
            imitate = request.POST.get(f"imitate{i + 1}")
            imitate = imitate[:-2]
            if imitate == "模倣曲" :
                imitate = request.POST.get(f"imitateimitate{i + 1}")
                if imitate :
                    ins_imitate, _ = Song.objects.get_or_create(title = imitate, defaults = {"title" : imitate})
                    imitates.add(ins_imitate.id)
            elif imitate != "オリジナル" :
                ins_imitate = Song.objects.filter(title = imitate).first()
                imitates.add(ins_imitate.id)

        if iscreated or not(iscreated or ins_song.imitate) :
            ins_song.imitate = list(imitates).join(",")
        ins_song.save()
        
        dir["ins_song"] = ins_song
        return render(request, 'subeana/song.html', dir)

    dir["basedir"] = get_basedir()
    if "channel" in request.GET :
        dir["channel"] = request.GET.get("channel")
    if "title" in request.GET :
        dir["title"] = request.GET.get("title")
    return render(request, 'subeana/new.html', dir)


def song(request, song_id) :
    dir = {}
    ins_song = Song.objects.get(pk = song_id)
    dir["ins_song"] = ins_song
    imitates = []
    if ins_song.isjoke :
        imitates.append("ネタ曲")
    if ins_song.imitate :
        for imitate_id in ins_song.imitate.split(",") :
            imitates.append(Song.objects.get(pk = imitate_id))
        dir["imitates"] = imitates
    return render(request, "subeana/song.html", dir)


def make(request) :
    dir = {}
    dir["ins_songs"] = Song.objects.all()
    dir["basedir"] = get_basedir()

    if request.method == "POST" :
        inp_genetype = request.POST.get("genetype")
        dir["genetype"] = inp_genetype
        if inp_genetype == "category" :
            inp_category = request.POST.get("category")
            dir["category"] = inp_category

            ins_imitates = set()
            ins_original = Song.objects.filter(title = inp_category[:-2]).first()
            for ins_song in Song.objects.all() :
                if ins_song.title == inp_category[:-2] :
                    ins_imitates.add(ins_song)
                elif ins_song.imitate :
                    if ins_original.id in ins_song.imitate.split(","):
                        ins_imitates.add(ins_song)
        
            ais_ins = vector_generate(ins_original, ins_imitates)
            dir["ais_ins"] = ais_ins
            return render(request, "subeana/result.html", dir)
                
        elif inp_genetype == "song" :
            inp_title = request.POST.get("title")
            dir["title"] = inp_title
            inp_similar = request.POST.get("similar")
            dir["similar"] = inp_similar

            imitates = []
            for ins_song in Song.objects.all() :
                name = ins_song.id
                if ins_song.imitate :
                    for imitate in ins_song.imitate.split(",") :
                        imitates.append((name, imitate, 1))

            G = nx.Graph()
            G.add_weighted_edges_from(imitates, weight='weight')

            ins_original = Song.objects.filter(title = inp_title).first()
            if ins_original.id in G.nodes() :
                length, path = nx.single_source_dijkstra(G, ins_original.id)
            else :
                dir["error"] = ins_original.title + "の模倣関係の曲が無いか登録されていないようです"
                return render(request, "subeana/make.html", dir)

            inp_pops = 5 - int(inp_similar)
            ins_imitates = set()
            for id, pops in length.items() :
                if pops <= inp_pops :
                    ins_imitates.add(Song.objects.get(pk = id))
            
            ais_ins = vector_generate(ins_original, ins_imitates)
            dir["basedir"] = get_basedir()
            dir["ais_ins"] = ais_ins
            return render(request, "subeana/result.html", dir)


        elif inp_genetype == "model" :
            0



    return render(request, "subeana/make.html", dir)


def channel(request, channel_name) :
    dir = {}

    dir["channel"] = channel_name
    ins_songs = Song.objects.filter(channel = channel_name)
    dir["ins_songs"] = ins_songs
    dir["basedir"] = get_basedir()
    if 3 > len(ins_songs) :
        dir["fixfooter"] = True
    return render(request, "subeana/channel.html", dir)


def edit(request) :
    dir = {}
    if "id" in request.GET :
        song_id = request.GET.get("id")
        ins_song = Song.objects.filter(pk = song_id)
        if len(ins_song) :
            ins_song = ins_song.first()
            dir["ins_song"] = ins_song
        else :
            return render(request, "subeana/error.html")
    else :
        return render(request, "subeana/error.html")
    
    if request.method == "POST" :
        inp_url = request.POST.get("url")
        inp_lyrics = request.POST.get("lyrics")

        if inp_url :
            if "https://www.youtube.com/watch" in inp_url :
                ins_song.url = format_url(inp_url)
            else :
                ins_song.url = inp_url
        if inp_lyrics :
            ins_song.lyrics = inp_lyrics

        ins_song.save()
        dir["ins_song"] = ins_song
        return render(request, "subeana/song.html", dir)

    return render(request, "subeana/edit.html", dir)


def search(request) :
    dir = {}

    if "lacks" in request.GET :
        dir["lacks"] = request.GET.get("lacks")
    if "nones" in request.GET :
        dir["nones"] = request.GET.get("nones")
    
    ins_songs = Song.objects.all()
    dir["ins_songs"] = ins_songs
    return render(request, "subeana/search.html", dir)


def error(request) :
    return render(request, "subeana/error.html")


def dev(request) :
    dir = {"locked" : True}
    if request.method == "POST":
        password = request.POST.get("password")
        dir["basedir"] = get_basedir()

        if password :
            if hashlib.sha256(password.encode()).hexdigest() == SHA256a :
                dir["locked"] = False
        else :
            Song.objects.all().delete()

            for song in SUBEANA_LIST :
                requests.post(url = get_basedir() + "/subeana/api/song/?format=json" ,data = song)
            
    return render(request, "subeana/dev.html", dir)


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class AiViewSet(viewsets.ModelViewSet):
    queryset = Ai.objects.all()
    serializer_class = AiSerializer