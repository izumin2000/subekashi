from django.shortcuts import render
from django.http import HttpResponseRedirect
from subekashi.models import Song, Ai, Genecategory, Genesong, Singleton
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
import re

# パスワード関連
SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"
REPLACEBLE_HINSHIS = ["名詞", "動詞", "形容詞"]


def getAPI(url) :
    try :
        get = requests.get(url)
    except :        # プロキシエラー等のエラーが発生したら
        print("5xx Error")
        return ""

    if (get.status_code == 200) :
        try :
            getDict = get.json()
        except :        # JSON形式ではなかったら（メンテナンス等）
            print("Not JSON Error", get.status_code)
            return ""

        if "error" in getDict :     # dictのキーにerrorがあったら
            print("Invalid path Error", get.status_code)
            return ""
        
        if "message" in getDict :     # dictのキーにerrorがあったら
            print("404 on json API", get.status_code)
            
        else :      # 正常に取得できたら
            print("OK", get.status_code)
            return getDict

    else :      # エラーステータスコードを受け取ったら（HEROKU error等）
        print("not 2xx", get.status_code)
        return ""


def counter(word) :
    word = str(word)
    hiragana = [(i >= "ぁ") and (i <= "ゟ") for i in word].count(True)
    katakana = [(i >= "ァ") and (i <= "ヿ") for i in word].count(True)
    kanji = [(i >= "一") and (i <= "鿼") for i in word].count(True)
    return hiragana, katakana, kanji


def tokenizerJanome(text):
    tokL = []
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
        tokL.append((tok.surface, hinshi, katsuyou))
    return tokL

def vectorGenerate(originalIns, imitateInsL, dataD) :
    lyrics = ""
    simD = {}
    tokL = tokenizerJanome(originalIns.lyrics)    
    for imitateIns in imitateInsL :
        ruigoDict = imitateIns.ruigo
        if ruigoDict :
            for hinshiKatsuyou, words in eval(ruigoDict).items() :
                if hinshiKatsuyou in simD.keys() :
                    simD[hinshiKatsuyou] += words
                else :
                    simD[hinshiKatsuyou] = words

    hinshiBefore = ""
    for word, hinshi, katsuyou in tokL :
        if (hinshi in REPLACEBLE_HINSHIS) and not(word.isdigit()) :
            if (hinshi == "名詞") and (hinshiBefore == "名詞") :
                continue
            hinshiBefore = hinshi
            hinshiKatsuyou = hinshi + katsuyou
            if hinshiKatsuyou in simD.keys() :
                pickWords = [word]
                for pickword in simD[hinshiKatsuyou] :
                    pickWords.append(pickword)
                lyrics += random.choice(pickWords)
            else :
                lyrics += word
            # simD[hinshi + katsuyou].remove(sim)
        else :
            lyrics += word

        hinshiBefore = hinshi
    aiInsL = []
    for lyric in lyrics.split("\n") :
        if len(lyric) >= 2 :
            aiIns = Ai.objects.create()
            aiIns.lyrics = lyric
            aiIns.genetype = dataD["genetype"]
            aiIns.save()
            aiInsL.append(aiIns)
            if dataD["genetype"] == "category" :
                genecategoryIns = Genecategory.objects.create()
                genecategoryIns.ai = aiIns
                genecategoryIns.category = dataD["category"]
                genecategoryIns.save()
            elif dataD["genetype"] == "song" :
                genesongIns = Genesong.objects.create()
                genesongIns.ai = aiIns
                genesongIns.title = dataD["title"]
                genesongIns.similar = int(dataD["similar"])
                genesongIns.save()
    return aiInsL


def formatURL(url) :
    url = url.replace("m.youtube.com", "www.youtube.com")
    if "https://www.youtube.com/watch" in url :
        return "https://youtu.be/" + url[32:43]
    else :
        return url

def initD() :
    dataD = {"lastModified": Singleton.objects.filter(key = "lastModified").first().value}
    if DEBUG :
        dataD["baseURL"] = "http://subekashi.localhost:8000"
    else :
        dataD["baseURL"] = "https://subekashi.izmn.net"
    return dataD


def top(request):
    dataD = initD()
    songInsL = list(Song.objects.exclude(lyrics = ""))[:-7:-1]
    dataD["songInsL"] = songInsL
    lackInsL = list(Song.objects.filter(lyrics = "").exclude(channel = ""))
    lackInsL += list(Song.objects.filter(url = "").exclude(channel = ""))
    if lackInsL :
        lackInsL = random.sample(lackInsL, min(6, len(lackInsL)))
        dataD["lackInsL"] = lackInsL
    noneInsL = list(Song.objects.filter(channel = ""))
    if noneInsL :
        noneInsL = random.sample(noneInsL, min(6, len(noneInsL)))
        dataD["noneInsL"] = noneInsL
        dataD["imitateInsL"] = list(map(lambda x: f"原曲は{Song.objects.get(id=int(x.imitated)).title}です" if x.imitated else "原曲が紐づけされていません" ,noneInsL))
    aiInsL = Ai.objects.filter(score = 5)[::-1]
    if aiInsL :
        dataD["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]
    return render(request, 'subekashi/top.html', dataD)


def new(request) :
    dataD = initD()

    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        urlForm = request.POST.get("url")
        imitatesForm = request.POST.get("imitates")
        lyricsForm = request.POST.get("lyrics")
        isorginalForm = request.POST.get("isorginal")
        isdeletedForm = request.POST.get("isdeleted")
        isjapaneseForm = request.POST.get("isjapanese")
        isjokeForm = request.POST.get("isjoke")
        isdraftForm = request.POST.get("isdraft")

        if ("" in [titleForm, channelForm]) :
            return render(request, "subekashi/error.html")

        titleForm = titleForm.replace("/", "╱")
        songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm)

        if isdeletedForm :
            songIns.url = "非公開"
        else :
            songIns.url = formatURL(urlForm)
        
        nowImitateS = set(songIns.imitate.split(","))
        newimitateS = set(imitatesForm.split(","))
        appendImitateS = newimitateS - nowImitateS
        deleteImitateS = nowImitateS - newimitateS
        for imitateId in appendImitateS :
            imitatedIns = Song.objects.get(pk = imitateId)
            newImitatedIns = set(imitatedIns.imitated).add(songIns.id)
            imitatedIns.imitated = ",".join(newImitatedIns)
            imitatedIns.save()
        for imitateId in deleteImitateS :
            imitatedIns = Song.objects.get(pk = imitateId)
            set(imitatedIns.imitated).remove(songIns.id)
            imitatedIns.imitated = ",".join(newImitatedIns)
            imitatedIns.save()
        songIns.imitate = imitatesForm

        songIns.lyrics = lyricsForm
        songIns.isoriginal = int(bool(isorginalForm))
        songIns.isjapanese = int(bool(isjapaneseForm))
        songIns.isjoke = int(bool(isjokeForm))
        songIns.isdraft = int(bool(isdraftForm))
        songIns.save()
        
        imitateInsL = []
        if songIns.imitate :
            imitateInsL = list(map(lambda i : Song.objects.get(pk = int(i)), songIns.imitate.split(",")))
            dataD["imitateInsL"] = imitateInsL
        dataD["songIns"] = songIns
        dataD["isExist"] = True
        
        content = f'**{songIns.title}**\n\
        id : {songIns.id}\n\
        チャンネル : {songIns.channel}\n\
        URL : {songIns.url}\n\
        模倣 : {", ".join([imitate.title for imitate in imitateInsL])}\n'
        requests.post(SUBEKASHI_NEW_DISCORD_URL, data={'content': content})
        
        return render(request, 'subekashi/song.html', dataD)
    
    else :
        dataD["songInsL"] = Song.objects.all()
        dataD["id"] = request.GET.get("id")

        return render(request, 'subekashi/new.html', dataD)


def song(request, songId) :
    dataD = initD()
    songIns = Song.objects.get(pk = songId)
    isExist = bool(songIns)
    dataD["songIns"] = songIns
    dataD["isExist"] = isExist

    if isExist :
        if songIns.imitate :
            imitateInsL = []
            imitates = songIns.imitate.split(",")
            for imitateId in imitates:
                imitateInsQ = Song.objects.filter(id = int(imitateId))
                if imitateInsQ :
                    imitateIns = imitateInsQ.first()
                    imitateInsL.append(imitateIns)
                else :
                    songIns.imitate = imitates.remove(imitateId)
                    songIns.save()
            dataD["imitateInsL"] = imitateInsL

        if songIns.imitated :
            imitatedInsL = []
            imitateds = songIns.imitated.split(",")
            for imitatedId in imitateds:
                imitatedInsQ = Song.objects.filter(id = int(imitatedId))
                if imitatedInsQ :
                    imitatedIns = imitatedInsQ.first()
                    imitatedInsL.append(imitatedIns)
                else :
                    songIns.imitate = imitateds.remove(imitatedId)
                    songIns.save()
            dataD["imitatedInsL"] = imitatedInsL

    return render(request, "subekashi/song.html", dataD)


def delete(request) :
    dataD = initD()
    dataD["isExist"] = False

    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm)
        isdraftForm = request.POST.get("isdraft")
        requests.post(SUBEKASHI_QUESTION_DISCORD_URL, data={'content': f"ID：{songIns.id}\n理由：{isdraftForm}"})
    return render(request, 'subekashi/song.html', dataD)


def make(request) :
    dataD = initD()
    dataD["songInsL"] = Song.objects.all()

    if request.method == "POST" :
        genetypeForm = request.POST.get("genetype")

        # TODO model以外もAIを対応させる
        if genetypeForm != "model" :
            return render(request, "subekashi/make.html", dataD)
            
        dataD["genetype"] = genetypeForm
        if genetypeForm == "category" :
            categoryForm = request.POST.get("category")
            dataD["category"] = categoryForm

            if (categoryForm == "選択してください") :
                return render(request, "subekashi/error.html")

            imitateInsL = set()
            originalIns = Song.objects.filter(title = categoryForm[:-2]).first()
            for songIns in Song.objects.all() :
                if songIns.title == categoryForm[:-2] :
                    imitateInsL.add(songIns)
                elif songIns.imitate :
                    if originalIns.id in songIns.imitate.split(","):
                        imitateInsL.add(songIns)
        
            aiInsL = vectorGenerate(originalIns, imitateInsL, dataD)
            dataD["aiInsL"] = aiInsL
            return render(request, "subekashi/result.html", dataD)
                
        elif genetypeForm == "song" :
            titleForm = request.POST.get("title")
            dataD["title"] = titleForm
            similarForm = request.POST.get("similar")
            dataD["similar"] = similarForm

            if (titleForm == "") :
                return render(request, "subekashi/error.html")

            imitateInsL = []
            for songIns in Song.objects.all() :
                name = songIns.id
                if songIns.imitate :
                    for imitate in songIns.imitate.split(",") :
                        imitateInsL.append((name, imitate, 1))
                if songIns.imitated :
                    for imitated in songIns.imitated.split(",") :
                        imitateInsL.append((name, imitated, 1))
                

            G = nx.Graph()
            G.add_weighted_edges_from(imitateInsL, weight='weight')

            originalIns = Song.objects.filter(title = titleForm).first()
            
            if originalIns.id in G.nodes() :
                length, _ = nx.single_source_dijkstra(G, originalIns.id)
            else :
                length = 0

            inp_pops = 5 - int(similarForm)
            imitateInsL = set([originalIns])
            disableGene = True
            if length :
                for id, pops in length.items() :
                    if pops <= inp_pops :
                        songIns = Song.objects.get(pk = id)
                        if not(songIns.isjoke) and songIns.isjapanese :
                            imitateInsL.add(songIns)
                            if disableGene :
                                if songIns.ruigo :
                                    disableGene = False
            
            if disableGene :
                dataD["error"] = "生成に必要なデータが揃ってないようです"
                return render(request, "subekashi/make.html", dataD)
            else :
                aiInsL = vectorGenerate(originalIns, imitateInsL, dataD)
                dataD["aiInsL"] = aiInsL
                return render(request, "subekashi/result.html", dataD)

        elif genetypeForm == "model" :
            aiIns = Ai.objects.filter(genetype = "model", score = 0)
            if not(len(aiIns)) :
                requests.post(SUBEKASHI_QUESTION_DISCORD_URL, data={'content': "aiInsのデータがありません。", "avatar_url": "https://publicdomainvectors.org/photos/Anonymous_attention.png"})
            # aiIns = Ai.objects.filter(genetype = "model")
            dataD["aiInsL"] = random.sample(list(aiIns), 25)
            return render(request, "subekashi/result.html", dataD)

    return render(request, "subekashi/make.html", dataD)


def channel(request, channelName) :
    dataD = initD()

    dataD["channel"] = channelName
    songInsL = Song.objects.filter(channel = channelName)
    dataD["songInsL"] = songInsL
    if 3 > len(songInsL) :
        dataD["fixfooter"] = True
    return render(request, "subekashi/channel.html", dataD)


def search(request) :
    dataD = initD()

    #TODO request.GETから必要なカラムだけ
    if "lacks" in request.GET :
        dataD["lacks"] = request.GET.get("lacks")
    if "nones" in request.GET :
        dataD["nones"] = request.GET.get("nones")
    if "isoriginal" in request.GET :
        dataD["isoriginal"] = request.GET.get("isoriginal")
    if "isjoke" in request.GET :
        dataD["isjoke"] = request.GET.get("isjoke")
    
    songInsL = Song.objects.all()
    dataD["songInsL"] = songInsL
    return render(request, "subekashi/search.html", dataD)


def ai(request) :
    aiInsL = list(Ai.objects.filter(genetype = "model", score = 5))[:-300:-1]
    return render(request, "subekashi/ai.html", {"aiInsL" : aiInsL})


def research(request) :
    if request.method == "POST":
        question = request.POST.get("question")
        requests.post(SUBEKASHI_QUESTION_DISCORD_URL, data={'content': question})
    return render(request, "subekashi/research.html")


def error(request) :
    return render(request, "subekashi/error.html")


def dev(request) :
    dataD = initD()
    dataD = {"locked" : True}
    if request.method == "POST":
        password = request.POST.get("password")

        if password :
            if hashlib.sha256(password.encode()).hexdigest() == SHA256a :
                dataD["locked"] = False
        isreset = request.GET.get("reset")
        isgpt = request.GET.get("gpt")
        iskey = request.GET.get("key")
        if isreset :
            Song.objects.all().delete()
            inp_isconfirmed = request.POST.get("confirm")
            isconfirmed = bool(inp_isconfirmed)
            if isconfirmed :
                for song in subeana_LIST :
                    songIns = Song.objects.create()
                    songIns.title = song["title"]
                    songIns.channel = song["channel"]
                    songIns.url = song["url"]
                    songIns.lyrics = song["lyrics"]
                    songIns.isjapanese = song["isjapanese"]
                    songIns.save()
                dataD["locked"] = False

        if isgpt :
            inp_gpt = request.POST.get("gpt")
            if inp_gpt :
                gpt_lines = inp_gpt.split("\n")[12:]
                gpt_lines = [i for i in gpt_lines if i[0] != "="]
                gpt_lines = sum(list(map(lambda i : re.split("、|。|？", i), gpt_lines)), [])
                gpt_lines = set(map(lambda i : re.sub("「|」|（|）|(|)|[ -¡]", "", i), gpt_lines))
                gpt_lines = [i for i in gpt_lines if 6 < len(i) < 22]
                [Ai.objects.create(lyrics = i, genetype = "model").save() for i in gpt_lines]

                dataD["locked"] = False
        if iskey :
            inp_key = request.POST.get("key")
            inp_value = request.POST.get("value")
            ins_singleton, _ = Singleton.objects.update_or_create(key = inp_key, defaults = {"key": inp_key})
            ins_singleton.key = inp_key
            ins_singleton.value = inp_value
            ins_singleton.save()
            
    return render(request, "subekashi/dev.html", dataD)


class SongViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class AiViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ai.objects.all()
    serializer_class = AiSerializer