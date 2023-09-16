from django.shortcuts import render, redirect
from subekashi.models import Song, Ai, Singleton
import hashlib
import requests
from .reset import subeana_LIST
import random
import random
from rest_framework import viewsets
from .serializer import SongSerializer, AiSerializer
from config.settings import *
import re
from django.utils import timezone


# パスワード関連
SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"
REPLACEBLE_HINSHIS = ["名詞", "動詞", "形容詞"]


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
        dataD["baseURL"] = "https://lyrics.imicomweb.com"
    return dataD


def sendDiscord(url, content) :
    res = requests.post(url, data={'content': content})
    return res.status_code


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
        
    if request.method == "POST":
        feedback = request.POST.get("feedback")
        sendDiscord(FEEDBACK_DISCORD_URL, feedback)
        
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
        songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm, defaults={"posttime" : timezone.now()})

        if isdeletedForm :
            songIns.url = "非公開"
        else :
            songIns.url = formatURL(urlForm)
        
        oldImitateS = set(songIns.imitate.split(",")) - set([''])
        newImitateS = set(imitatesForm.split(",")) - set([''])

        appendImitateS = newImitateS - oldImitateS
        deleteImitateS = oldImitateS - newImitateS

        for imitateId in appendImitateS :
            imitatedIns = Song.objects.get(pk = imitateId)
            imitatedInsL = set(imitatedIns.imitated.split(","))
            imitatedInsL.add(str(songIns.id))
            imitatedIns.imitated = ",".join(imitatedInsL)
            imitatedIns.posttime = timezone.now()
            imitatedIns.save()
        for imitateId in deleteImitateS :
            imitatedIns = Song.objects.get(pk = imitateId)
            imitatedInsL = set(imitatedIns.imitated.split(","))
            imitatedInsL.remove(str(songIns.id))
            imitatedIns.imitated = ",".join(imitatedInsL)
            imitatedIns.posttime = timezone.now()
            imitatedIns.save()
        songIns.imitate = imitatesForm

        songIns.lyrics = lyricsForm
        songIns.isoriginal = int(bool(isorginalForm))
        songIns.isjapanese = int(bool(isjapaneseForm))
        songIns.isjoke = int(bool(isjokeForm))
        songIns.isdraft = int(bool(isdraftForm))
        songIns.posttime = timezone.now()
        forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_addresses:
            songIns.ip = forwarded_addresses.split(',')[0]
        else:
            songIns.ip = request.META.get('REMOTE_ADDR')
        songIns.save()
        
        imitateInsL = []
        if songIns.imitate :
            imitateInsL = list(map(lambda i : Song.objects.get(pk = int(i)), songIns.imitate.split(",")))
            dataD["imitateInsL"] = imitateInsL
        dataD["songIns"] = songIns
        dataD["isExist"] = True

        content = f'**{songIns.title}**\n\
        {ROOT_DIR}/songs/{songIns.id}\n\
        チャンネル : {songIns.channel}\n\
        URL : {songIns.url}\n\
        模倣 : {", ".join([imitate.title for imitate in imitateInsL])}\n\
        ネタ曲 : {"Yes" if songIns.isjoke else "No"}\n\
        IP : {songIns.ip}\n\
        歌詞 : ```{songIns.lyrics}```\n\
        \n'
        requests.post(NEW_DISCORD_URL, data={'content': content})
        
        return render(request, 'subekashi/song.html', dataD)
    
    else :
        dataD["songInsL"] = Song.objects.all()
        dataD["id"] = request.GET.get("id")

        return render(request, 'subekashi/new.html', dataD)


def song(request, songId) :
    dataD = initD()
    songIns = Song.objects.filter(pk = songId).first()
    isExist = bool(songIns)
    dataD["songIns"] = songIns
    dataD["isExist"] = isExist

    if isExist :
        if songIns.imitate :
            imitateInsL = []
            imitates = songIns.imitate.split(",")
            for imitateId in imitates:
                if imitateId.isdigit() :
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
                if imitatedId.isdigit() :
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
    dataD["isDeleted"] = True

    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm, defaults={"posttime" : timezone.now()})
        reasonForm = request.POST.get("reason")
        content = f"ID：{songIns.id}\n理由：{reasonForm}"
        statusCode = sendDiscord(DELETE_DISCORD_URL, content)
        print(statusCode)
        if statusCode != 204 :
            return render(request, 'subekashi/error.html', dataD)
        
    return render(request, 'subekashi/song.html', dataD)


def make(request) :
    dataD = initD()
    dataD["songInsL"] = Song.objects.all()

    if request.method == "POST" :
        genetypeForm = request.POST.get("genetype")

        # TODO model以外もAIを対応させる
        if genetypeForm == "model" :
            aiIns = Ai.objects.filter(genetype = "model", score = 0)
            if not(len(aiIns)) :
                sendDiscord(ERROR_DISCORD_URL, "aiInsのデータがありません。")
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
    dataD["songInsL"] = Song.objects.order_by("-posttime")
    query = request.GET
    dataD["query"] = f"{query.get('title')},{query.get('channel')},{query.get('lyrics')},{query.get('filter')}".replace("None", "")
    return render(request, "subekashi/search.html", dataD)


def ai(request) :
    aiInsL = list(Ai.objects.filter(genetype = "model", score = 5))[:-300:-1]
    return render(request, "subekashi/ai.html", {"aiInsL" : aiInsL})


def research(request) :
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
                    songIns.posttime = timezone.now()
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


def github(request) :
    return redirect("https://github.com/izumin2000/subekashi")


def robots(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/robots.txt")


def sitemap(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/sitemap.xml")


class SongViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class AiViewSet(viewsets.ModelViewSet):
    queryset = Ai.objects.all()
    serializer_class = AiSerializer