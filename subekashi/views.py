from django.shortcuts import render
from django.http import HttpResponseRedirect
from subekashi.models import Song, Ai, Genecategory, Genesong
from config.settings import DEBUG
import hashlib
import requests
from time import sleep
from .reset import subeana_LIST
import random
from janome.tokenizer import Tokenizer
import networkx as nx
import random
from rest_framework import viewsets
from .serializer import SongSerializer, AiSerializer
from config.settings import *
from django.contrib.auth.views import LogoutView
from django.urls import reverse

# パスワード関連
SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"
REPLACEBLE_HINSHIS = ["名詞", "動詞", "形容詞"]


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
    if DEBUG :
        return "http://subekashi.localhost:8000"
    else :
        return "https://subekashi.izmn.net"


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

def vector_generate(ins_original, ins_imitates, dir) :
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
    ins_ais = []
    for lyric in lyrics.split("\n") :
        if len(lyric) >= 2 :
            ins_ai = Ai.objects.create()
            ins_ai.lyrics = lyric
            ins_ai.genetype = dir["genetype"]
            ins_ai.save()
            ins_ais.append(ins_ai)
            if dir["genetype"] == "category" :
                ins_genecategory = Genecategory.objects.create()
                ins_genecategory.ai = ins_ai
                ins_genecategory.category = dir["category"]
                ins_genecategory.save()
            elif dir["genetype"] == "song" :
                ins_genesong = Genesong.objects.create()
                ins_genesong.ai = ins_ai
                ins_genesong.title = dir["title"]
                ins_genesong.similar = int(dir["similar"])
                ins_genesong.save()
    return ins_ais


def format_url(url) :
    if "https://www.youtube.com/watch" in url :
        return "https://youtu.be/" + url[32:43]
    else :
        return url


def top(request):
    dir = {}
    ins_songs = list(Song.objects.exclude(lyrics = ""))[:-7:-1]
    dir["ins_songs"] = ins_songs
    ins_lacks = list(Song.objects.filter(lyrics = "").exclude(channel = ""))
    ins_lacks += list(Song.objects.filter(url = "").exclude(channel = ""))
    if ins_lacks :
        ins_lacks = random.sample(ins_lacks, min(6, len(ins_lacks)))
        dir["ins_lacks"] = ins_lacks
    ins_nones = list(Song.objects.filter(channel = ""))
    if ins_nones :
        ins_nones = random.sample(ins_nones, min(6, len(ins_nones)))
        dir["ins_nones"] = ins_nones
    ins_ais = Ai.objects.filter(score = 0)[::-1]
    if ins_ais :
        dir["ins_ais"] = ins_ais[min(10, len(ins_ais))::-1]
    dir["basedir"] = get_basedir()
    return render(request, 'subekashi/top.html', dir)


def new(request) :
    dir = {}

    if request.method == "POST":
        inp_title = request.POST.get("title")
        inp_channel = request.POST.get("channel")
        inp_url = request.POST.get("url")
        inp_lyrics = request.POST.get("lyrics")
        inp_isjapanese = request.POST.get("isjapanese")
        inp_isjoke = request.POST.get("isjoke")
        imitate1 = request.POST.get("imitate1")

        if (("" in [inp_title, inp_channel]) or (imitate1 == "選択してください")):
            return render(request, "subekashi/error.html")

        ins_song, iscreated = Song.objects.get_or_create(title = inp_title, defaults = {"title" : inp_title})

        ins_song.title = inp_title
        if iscreated or not(iscreated or ins_song.channel) :
            ins_song.channel = inp_channel.replace(" ", "")
        ins_song.isjapanese = bool(inp_isjapanese)
        ins_song.isjoke = bool(inp_isjoke)

        if inp_url and (iscreated or not(iscreated or ins_song.url)):
            ins_song.url = format_url(inp_url)
        if inp_lyrics and (iscreated or not(iscreated or ins_song.lyrics)) :
            ins_song.lyrics = inp_lyrics

        imitates = set()
        imitateNum = 1
        while 1 :
            imitate = request.POST.get(f"imitate{imitateNum}")
            if imitate :
                imitate = imitate[:-2]
                if imitate == "模倣曲" :
                    imitate = request.POST.get(f"imitateimitate{imitateNum}")
                    if imitate :
                        ins_imitate, _ = Song.objects.get_or_create(title = imitate, defaults = {"title" : imitate})
                        imitates.add(ins_imitate.id)
                        if ins_imitate.imitated :
                            imitated = set(ins_imitate.imitated.split(","))
                            imitated.add(ins_song.id)
                            ins_imitate.imitated = ",".join(list(map(str, imitated)))
                        else :
                            ins_imitate.imitated = ins_song.id
                        ins_imitate.save()
                elif imitate == "オリジナル" :
                    ins_song.isoriginal = True
                else :
                    ins_imitate = Song.objects.filter(title = imitate).first()
                    imitates.add(ins_imitate.id)
                    if ins_imitate.imitated :
                        imitated = set(ins_imitate.imitated.split(","))
                        imitated.add(ins_song.id)
                        ins_imitate.imitated = ",".join(list(map(str, imitated)))
                    else :
                        ins_imitate.imitated = ins_song.id
                    ins_imitate.save()
                imitateNum += 1
            else :
                break

        if iscreated or not(iscreated or ins_song.imitate) :
            ins_song.imitate = ",".join(list(map(str, list(imitates))))
        ins_song.save()
        
        imitates = []
        if ins_song.imitate :
            for imitate_id in ins_song.imitate.split(",") :
                imitates.append(Song.objects.get(pk = int(imitate_id)))
            dir["imitates"] = imitates
        dir["ins_song"] = ins_song
        content = f'**{ins_song.title}**\n\
        id : {ins_song.id}\n\
        チャンネル : {ins_song.channel}\n\
        URL : {ins_song.url}\n\
        模倣 : {", ".join([imitate.title for imitate in imitates])}\n\
        歌詞 : {ins_song.lyrics[:min(20, len(ins_song.lyrics))]}'
        requests.post(SUBEKASHI_NEW_DISCORD_URL, data={'content': content})
        return render(request, 'subekashi/song.html', dir)

    dir["basedir"] = get_basedir()
    if "channel" in request.GET :
        dir["channel"] = request.GET.get("channel")
    if "title" in request.GET :
        dir["title"] = request.GET.get("title")
    return render(request, 'subekashi/new.html', dir)


def song(request, song_id) :
    dir = {}
    ins_song = Song.objects.get(pk = song_id)
    dir["ins_song"] = ins_song

    imitates = []
    if ins_song.imitate :
        for imitate_id in ins_song.imitate.split(",") :
            imitates.append(Song.objects.get(pk = int(imitate_id)))
        dir["imitates"] = imitates

    imitateds = ins_song.imitated
    if imitateds :
        ins_imitateds = []
        for id in imitateds.split(",") :
            ins_imitated = Song.objects.get(pk = int(id))
            ins_imitateds.append(ins_imitated)
        dir["ins_imitateds"] = ins_imitateds

    return render(request, "subekashi/song.html", dir)


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

            if (inp_category == "選択してください") :
                return render(request, "subekashi/error.html")

            ins_imitates = set()
            ins_original = Song.objects.filter(title = inp_category[:-2]).first()
            for ins_song in Song.objects.all() :
                if ins_song.title == inp_category[:-2] :
                    ins_imitates.add(ins_song)
                elif ins_song.imitate :
                    if ins_original.id in ins_song.imitate.split(","):
                        ins_imitates.add(ins_song)
        
            ins_ais = vector_generate(ins_original, ins_imitates, dir)
            dir["ins_ais"] = ins_ais
            return render(request, "subekashi/result.html", dir)
                
        elif inp_genetype == "song" :
            inp_title = request.POST.get("title")
            dir["title"] = inp_title
            inp_similar = request.POST.get("similar")
            dir["similar"] = inp_similar

            if (inp_title == "") :
                return render(request, "subekashi/error.html")

            imitates = []
            for ins_song in Song.objects.all() :
                name = ins_song.id
                if ins_song.imitate :
                    for imitate in ins_song.imitate.split(",") :
                        imitates.append((name, imitate, 1))
                if ins_song.imitated :
                    for imitated in ins_song.imitated.split(",") :
                        imitates.append((name, imitated, 1))
                

            G = nx.Graph()
            G.add_weighted_edges_from(imitates, weight='weight')

            ins_original = Song.objects.filter(title = inp_title).first()
            
            if ins_original.id in G.nodes() :
                length, _ = nx.single_source_dijkstra(G, ins_original.id)
            else :
                length = 0

            inp_pops = 5 - int(inp_similar)
            ins_imitates = set([ins_original])
            disableGene = True
            if length :
                for id, pops in length.items() :
                    if pops <= inp_pops :
                        ins_song = Song.objects.get(pk = id)
                        if not(ins_song.isjoke) and ins_song.isjapanese :
                            ins_imitates.add(ins_song)
                            if disableGene :
                                if ins_song.ruigo :
                                    disableGene = False
            
            if disableGene :
                dir["error"] = "生成に必要なデータが揃ってないようです"
                return render(request, "subekashi/make.html", dir)
            else :
                ins_ais = vector_generate(ins_original, ins_imitates, dir)
                dir["basedir"] = get_basedir()
                dir["ins_ais"] = ins_ais
                return render(request, "subekashi/result.html", dir)

        elif inp_genetype == "model" :
            ins_ai = Ai.objects.filter(genetype = "model").exclude(score = 0)
            dir["ins_ais"] = random.sample(list(ins_ai), 20)
            return render(request, "subekashi/result.html", dir)

    return render(request, "subekashi/make.html", dir)


def channel(request, channel_name) :
    dir = {}

    dir["channel"] = channel_name
    ins_songs = Song.objects.filter(channel = channel_name)
    dir["ins_songs"] = ins_songs
    dir["basedir"] = get_basedir()
    if 3 > len(ins_songs) :
        dir["fixfooter"] = True
    return render(request, "subekashi/channel.html", dir)


def edit(request) :
    dir = {}
    if "id" in request.GET :
        song_id = request.GET.get("id")
        ins_song = Song.objects.filter(pk = song_id)
        if len(ins_song) :
            ins_song = ins_song.first()
            dir["ins_song"] = ins_song
        else :
            return render(request, "subekashi/error.html")
    else :
        return render(request, "subekashi/error.html")
    
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
        content = f'**{ins_song.title}**\n\
        id : {ins_song.id}\n\
        チャンネル : {ins_song.channel}\n\
        URL : {ins_song.url}\n\
        歌詞 : {ins_song.lyrics[:min(20, len(ins_song.lyrics))]}'
        requests.post(SUBEKASHI_NEW_DISCORD_URL, data={'content': content})
        return render(request, "subekashi/song.html", dir)

    return render(request, "subekashi/edit.html", dir)


def search(request) :
    dir = {}

    if "lacks" in request.GET :
        dir["lacks"] = request.GET.get("lacks")
    if "nones" in request.GET :
        dir["nones"] = request.GET.get("nones")
    if "isoriginal" in request.GET :
        dir["isoriginal"] = request.GET.get("isoriginal")
    if "isjoke" in request.GET :
        dir["isjoke"] = request.GET.get("isjoke")
    
    ins_songs = Song.objects.all()
    dir["basedir"] = get_basedir()
    dir["ins_songs"] = ins_songs
    return render(request, "subekashi/search.html", dir)


def wrong(request, song_id) :
    dir = {}

    ins_song = Song.objects.get(pk = song_id)
    dir["ins_song"] = ins_song
    if request.method == "POST" :
        inp_reason = request.POST.get("reason")
        inp_comment = request.POST.get("comment")
        if inp_comment :
            content = f'**{ins_song.title}**\nid : {ins_song.id}\n理由 : {inp_reason}\nコメント : {inp_comment}'
        else :
            content = f'**{ins_song.title}**\nid : {ins_song.id}\n理由 : {inp_reason}'
        requests.post(SUBEKASHI_EDIT_DISCORD_URL, data={'content': content})

    return render(request, "subekashi/wrong.html", dir)


def ai(request) :
    dir = {}
    dir["ins_ais"] = Ai.objects.filter(score = 0)[::-1]
    return render(request, "subekashi/ai.html", dir)


def note(request) :
    return render(request, "subekashi/note.html")


def error(request) :
    return render(request, "subekashi/error.html")


def dev(request) :
    dir = {"locked" : True}
    if request.method == "POST":
        password = request.POST.get("password")
        dir["basedir"] = get_basedir()

        if password :
            if hashlib.sha256(password.encode()).hexdigest() == SHA256a :
                dir["locked"] = False
        isreset = request.GET.get("reset")
        isgpt = request.GET.get("gpt")
        if isreset :
            Song.objects.all().delete()
            inp_isconfirmed = request.POST.get("confirm")
            isconfirmed = bool(inp_isconfirmed)
            if isconfirmed :
                for song in subeana_LIST :
                    ins_song = Song.objects.create()
                    ins_song.title = song["title"]
                    ins_song.channel = song["channel"]
                    ins_song.url = song["url"]
                    ins_song.lyrics = song["lyrics"]
                    ins_song.isjapanese = song["isjapanese"]
                    ins_song.save()
                dir["locked"] = False

        if isgpt :
            inp_gpt = request.POST.get("gpt")
            if inp_gpt :
                set_lyrics = set()
                gpts = inp_gpt.split("\n")[12:]
                for gpt in gpts :
                    if gpt[0] != "=" :
                        sentence_gpts = gpt.split("。")
                        for sentence_gpt in sentence_gpts :
                            sentence_gpt += "。"
                            lyrics_gpts = sentence_gpt.split("、")
                            for lyrics_gpt in lyrics_gpts :
                                for delete_char in "「」　（）()" :
                                    lyrics_gpt = lyrics_gpt.replace(delete_char, "")
                                set_lyrics.add(lyrics_gpt)

                lyrics_tmp = ""
                for ai_lyrics in set_lyrics :
                    if lyrics_tmp :
                        ai_lyrics += lyrics_tmp
                    if len(ai_lyrics) <= 7 :
                        lyrics_tmp = ai_lyrics
                    elif len(ai_lyrics) <= 20 :
                        if (ai_lyrics[-1] != "、") and (ai_lyrics[-1] != "。") :
                            ai_lyrics += "、"
                        ins_ai = Ai.objects.create()
                        ins_ai.lyrics = ai_lyrics
                        ins_ai.save()
                        lyrics_tmp = ""

                dir["locked"] = False
            
    return render(request, "subekashi/dev.html", dir)


class SongViewSet(viewsets.ModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class AiViewSet(viewsets.ModelViewSet):
    queryset = Ai.objects.all()
    serializer_class = AiSerializer


def Login(request):
    return HttpResponseRedirect(reverse('social:begin', kwargs=dict(backend='google-oauth2')))

    
class Logout(LogoutView):
    next_page = '/'