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
        # elif hinshi == "名詞" :
            # katsuyou = tok.part_of_speech
        else :
            katsuyou = ""
        toklist.append((tok.surface, hinshi, katsuyou))
    return toklist


def vector_generate(ins_original, ins_songs) :
    lyrics = ""
    simD = {}
    tok = tokenizer_janome(ins_original.lyrics)
    
    for ins_song in ins_songs :
        ruigo = ins_song.ruigo
        if ruigo :
            for hinshi, words in eval(ruigo).items() :
                if hinshi in simD.keys() :
                    simD[hinshi] += words
                else :
                    simD[hinshi] = words

    for word, hinshi, katsuyou in tok :
        if hinshi in REPLACEBLE_HINSHIS :
            if (hinshi + katsuyou) in simD.keys() :
                # fitL = [sim for sim in simD[hinshi + katsuyou] if counter(word) == counter(sim)]
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
    
    ais_ins = []
    for lyric in lyrics.split("\n") :
        ai_ins = Ai.objects.create()
        ai_ins.lyrics = lyric
        ai_ins.save()
        ais_ins.append(ai_ins)
    return ais_ins


def top(request):
    dir = {}
    ins_songs = Song.objects.exclude(lyrics = "")
    dir["ins_songs"] = ins_songs.reverse()
    pages = len(ins_songs)
    dir["pages"] = list(range(1, pages + 1))
    return render(request, 'subeana/top.html', dir)


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
            if "https://www.youtube.com/watch" in inp_url :
                url = "https://youtu.be/" + inp_url[32:44]
                ins_song.url = url
            else :
                ins_song.url = inp_url
        if inp_lyrics :
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
            elif imitate != "オリジナル模倣" :
                ins_imitate = Song.objects.filter(title = imitate).first()
                imitates.add(ins_imitate.id)

        ins_song.imitate = str(list(imitates))
        ins_song.save()

    dir["basedir"] = get_basedir()
    return render(request, 'subeana/new.html', dir)


def song(request, song_id) :
    dir = {}
    ins_song = Song.objects.get(pk = song_id)
    dir["ins_song"] = ins_song
    imitates = []
    if ins_song.imitate :
        print(ins_song.imitate)
        for imitate_id in eval(ins_song.imitate) :
            imitates.append(Song.objects.get(pk = imitate_id))
        dir["imitates"] = imitates
    return render(request, "subeana/song.html", dir)


def make(request) :
    dir = {}

    if request.method == "POST":
        inp_genetype = request.POST.get("genetype")
        if inp_genetype == "category" :
            inp_category = request.POST.get("category")
            inp_similar = request.POST.get("similar")

            ins_songs = set()
            ins_original = Song.objects.filter(title = inp_category[:-2]).first()
            for ins_song in Song.objects.all() :
                if ins_song.title == inp_category[:-2] :
                    ins_songs.add(ins_song)
                elif ins_song.imitate :
                    if ins_original.id in eval(ins_song.imitate):
                        ins_songs.add(ins_song)
        
            ais_ins = vector_generate(ins_original, ins_songs)
            dir["basedir"] = get_basedir()
            dir["ais_ins"] = ais_ins
            return render(request, "subeana/result.html", dir)
                
        elif inp_genetype == "song" :
            inp_title = request.POST.get("title")
            inp_similar = request.POST.get("similar")

            imitates = []
            for ins_song in Song.objects.all() :
                name = ins_song.id
                if ins_song.imitate :
                    for imitate in eval(ins_song.imitate) :
                        #TODO ウェイトを1以外に
                        imitates.append((name, imitate, 1))

            G = nx.Graph()
            G.add_weighted_edges_from(imitates, weight='weight')

            ins_original = Song.objects.filter(title = inp_title).first()
            length, path = nx.single_source_dijkstra(G, ins_song.id)

            #TODO  ↓ をinp_similarに
            inp_pops = 2
            ins_songs = set()
            for id, pops in length.items() :
                if pops <= inp_pops :
                    ins_songs.add(Song.objects.get(pk = id))
            
            ais_ins = vector_generate(ins_original, ins_songs)
            dir["basedir"] = get_basedir()
            dir["ais_ins"] = ais_ins
            return render(request, "subeana/result.html", dir)


        elif inp_genetype == "model" :
            0



    
    dir["ins_songs"] = Song.objects.all()
    dir["basedir"] = get_basedir()
    return render(request, "subeana/make.html", dir)

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