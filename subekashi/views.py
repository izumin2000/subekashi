from django.shortcuts import render, redirect
from django.db.models import Q
from subekashi.models import *
import hashlib
import requests
import random
import random
from rest_framework import viewsets
from .serializer import *
from config.settings import *
import re
from django.utils import timezone
from django.core import management
from django.http import HttpResponse, JsonResponse
import json
import traceback


SHA256a = "5802ea2ddcf64db0efef04a2fa4b3a5b256d1b0f3d657031bd6a330ec54abefd"
INPUT_TEXTS = ["title", "channel", "lyrics", "url"]
INPUT_SELECTS = ["category", "songrange", "jokerange"]
INPUT_FLAGS = ["isdraft", "isoriginal", "isinst"]
URL_PATTERN = r'(?:\/|v=)([A-Za-z0-9_-]{11})(?:\?|&|$)'


def isYouTubeLink(link):
    videoID = re.search(URL_PATTERN, link)
    return videoID is not None


def formatURL(link):
    videoID = re.search(URL_PATTERN, link)
    if isYouTubeLink(link):
        return "https://youtu.be/" + videoID.group(1)
    else:
        return link


def sendDiscord(url, content) :
    res = requests.post(url, data={'content': content})
    return res.status_code


def sha256(check) :
    check += SECRET_KEY
    return hashlib.sha256(check.encode()).hexdigest()


def filter_by_category(queryset, category):
    return queryset.filter(
        Q(imitate=category) |
        Q(imitate__startswith=category + ',') |
        Q(imitate__endswith=',' + category) |
        Q(imitate__contains=',' + category + ',')
    )


islack = (
    ~Q(channel="全てあなたの所為です。") &
    (
        (Q(isdeleted=False) & Q(url="")) |
        (Q(isoriginal=False) & Q(issubeana=True) & Q(imitate="")) &
        (Q(isinst=False) & Q(lyrics=""))
    )
)


def top(request):
    dataD = dict()
    
    newsIns, _ = Singleton.objects.get_or_create(key = "news")
    dataD["news"] = newsIns.value
    
    songrange = request.COOKIES.get("songrange", "subeana")
    jokerange = request.COOKIES.get("jokerange", "off")
    
    if songrange == "all" :
        songInsL = Song.objects.all()
    elif songrange == "subeana" :
        songInsL = Song.objects.filter(issubeana = True)
    elif songrange == "xx" :
        songInsL = Song.objects.filter(issubeana = False)
    if jokerange == "off" :
        songInsL = songInsL.filter(isjoke = False)
        
    dataD["songInsL"] = list(songInsL)[:-7:-1]
    lackInsL = list(songInsL.filter(islack))
    if lackInsL :
        lackInsL = random.sample(lackInsL, min(6, len(lackInsL)))
        dataD["lackInsL"] = lackInsL
    aiInsL = Ai.objects.filter(score = 5)[::-1]
    
    if aiInsL :
        dataD["aiInsL"] = aiInsL[min(10, len(aiInsL))::-1]
        
    if request.method == "POST" :
        feedback = request.POST.get("feedback", None)
        if feedback : sendDiscord(FEEDBACK_DISCORD_URL, feedback)
        else :
            query = {key: value for key, value in request.POST.items() if value}
            songInsL = Song.objects.filter(**{f"{key}__icontains": value for key, value in query.items() if (key in INPUT_TEXTS)})
            query["songrange"] = request.COOKIES.get("songrange", "subeana")
            query["jokerange"] = request.COOKIES.get("jokerange", "off")
            
            if query["songrange"] == "subeana" : songInsL = songInsL.filter(issubeana = True)
            if query["songrange"] == "xx" : songInsL = songInsL.filter(issubeana = False)
            if query["jokerange"] == "off" : songInsL = songInsL.filter(isjoke = False)
            
            dataD["counter"] = f"{len(Song.objects.all())}曲中{len(songInsL)}曲表示しています。"
            dataD["query"] = query
            dataD["songInsL"] = songInsL.order_by("-posttime")
            return render(request, "subekashi/search.html", dataD)
    
    isAdDisplay = request.COOKIES.get("adrange", "off") == "on"
    dataD["isAdDisplay"] = isAdDisplay
    adInsL = Ad.objects.filter(status = "pass") if isAdDisplay else ""
    if adInsL :
        adInsL = random.sample(list(adInsL), min(len(adInsL), 10))
        adInsL = [adIns for adIns in adInsL for _ in range(adIns.dup)]
        adIns = random.choice(adInsL) if adInsL else []
        dataD["adIns"] = adIns
    
    return render(request, 'subekashi/top.html', dataD)


def new(request) :
    dataD = dict()

    if request.method == "POST":
        idForm = request.POST.get("songid")
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        urlForm = request.POST.get("url")
        imitatesForm = request.POST.get("imitates")
        lyricsForm = request.POST.get("lyrics")
        isorginalForm = request.POST.get("isorginal")
        isdeletedForm = request.POST.get("isdeleted")
        isjokeForm = request.POST.get("isjoke")
        isinstForm = request.POST.get("isinst")
        issubeanaForm = request.POST.get("issubeana")
        isdraftForm = request.POST.get("isdraft")

        if ("" in [titleForm, channelForm]) :
            return render(request, "subekashi/500.html")

        titleForm = titleForm.replace("/", "╱")
        if idForm :
            songIns = Song.objects.get(pk = int(idForm))
            songIns.title = titleForm
            songIns.channel = channelForm
        else :
            songIns, _ = Song.objects.get_or_create(title = titleForm, channel = channelForm, defaults={"posttime" : timezone.now()})
        
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
        songIns.url = formatURL(urlForm)
        songIns.isoriginal = int(bool(isorginalForm))
        songIns.isjoke = int(bool(isjokeForm))
        songIns.isdeleted = int(bool(isdeletedForm))
        songIns.isinst = int(bool(isinstForm))
        songIns.issubeana = int(bool(issubeanaForm))
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
        dataD["channels"] = songIns.channel.replace(", ", ",").split(",")
        dataD["urls"] = songIns.url.replace(", ", ",").split(",")
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
    dataD = dict()
    songIns = Song.objects.filter(pk = songId).first()
    isExist = bool(songIns)
    dataD["songIns"] = songIns
    dataD["isExist"] = isExist

    # TODO リファクタリング
    if isExist :
        dataD["channels"] = songIns.channel.replace(", ", ",").split(",")
        dataD["urls"] = songIns.url.replace(", ", ",").split(",") if songIns.url else []
        jokerange = request.COOKIES.get("jokerange", "off")
        if songIns.imitate :
            imitateInsL = []
            imitates = songIns.imitate.split(",")
            for imitateId in imitates:
                imitateInsQ = Song.objects.filter(id = int(imitateId))
                if imitateInsQ :
                    imitateIns = imitateInsQ.first()
                    if imitateIns.isjoke and (jokerange == "off") :
                        continue
                    imitateInsL.append(imitateIns)

            dataD["imitateInsL"] = imitateInsL

        if songIns.imitated :
            imitatedInsL = []
            imitateds = set(songIns.imitated.split(",")) - set([""])
            for imitatedId in imitateds :
                imitatedInsQ = Song.objects.filter(id = int(imitatedId))
                if imitatedInsQ :
                    imitatedIns = imitatedInsQ.first()
                    if imitatedIns.isjoke and (jokerange == "off") :
                        continue
                    imitatedInsL.append(imitatedIns)

            dataD["imitatedInsL"] = imitatedInsL
        return render(request, "subekashi/song.html", dataD)
    else :
        return render(request, 'subekashi/404.html', status=404)


def delete(request) :
    dataD = dict()
    dataD["isDeleted"] = True
    dataD["songInsL"] = Song.objects.all()
    
    if request.method == "POST":
        titleForm = request.POST.get("title")
        channelForm = request.POST.get("channel")
        songIns = Song.objects.filter(title = titleForm, channel = channelForm)
        if not songIns :
            return render(request, 'subekashi/500.html')
        songIns = songIns.first()
        reasonForm = request.POST.get("reason")
        content = f"ID：{songIns.id}\n理由：{reasonForm}"
        sendDiscord(DELETE_DISCORD_URL, content)
        
    return render(request, 'subekashi/song.html', dataD)


def ai(request) :
    dataD = dict()
    dataD["songInsL"] = Song.objects.all()

    if request.method == "POST" :
        aiIns = Ai.objects.filter(genetype = "model", score = 0)
        if len(aiIns) <= 25 :
            sendDiscord(ERROR_DISCORD_URL, "aiInsのデータがありません。")
            aiIns = Ai.objects.filter(genetype = "model")
        dataD["aiInsL"] = random.sample(list(aiIns), 25)
        return render(request, "subekashi/result.html", dataD)
    dataD["bestInsL"] = list(Ai.objects.filter(genetype = "model", score = 5))[:-300:-1]
    
    return render(request, "subekashi/ai.html", dataD)


def channel(request, channelName) :
    dataD = dict()
    dataD["channel"] = channelName
    songInsL = []
    for songIns in Song.objects.all() :
        if channelName in songIns.channel.replace(", ", ",").split(",") :
            songInsL.append(songIns)
    dataD["songInsL"] = songInsL
    return render(request, "subekashi/channel.html", dataD)


def search(request) :
    dataD = dict()
    query_select = {}
    
    if request.method == "GET" :
        songInsL = Song.objects.all()  
        query = {key: value for key, value in request.GET.items() if value}
        
        query_select_cookie = {key: value for key, value in request.COOKIES.items() if value and (key in INPUT_SELECTS)}
        query_select_url = {key: value for key, value in query.items() if value and (key in INPUT_SELECTS)}
        if ("songrange" in query_select_url) : query_select["songrange"] = query_select_url["songrange"]
        elif ("songrange" in query_select_cookie) : query_select["songrange"] = query_select_cookie["songrange"]
        else : query_select["songrange"] = "subeana"
        if ("jokerange" in query_select_url) : query_select["jokerange"] = query_select_url["jokerange"] 
        elif ("jokerange" in query_select_cookie) : query_select["jokerange"] = query_select_cookie["jokerange"] 
        else : query_select["jokerange"] = "off"
        if query_select["songrange"] == "subeana" : songInsL = songInsL.filter(issubeana = True)
        if query_select["songrange"] == "xx" : songInsL = songInsL.filter(issubeana = False)
        if query_select["jokerange"] == "off" : songInsL = songInsL.filter(isjoke = False)
        
        query_text = {f"{key}__icontains": value for key, value in query.items() if (key in INPUT_TEXTS)}
        songInsL = Song.objects.filter(**query_text)
        
        filter = request.GET.get("filter", "")
        query["filters"] = [filter]
        if filter == "islack" : songInsL = songInsL.filter(islack)
        elif filter : songInsL = songInsL.filter(**{filter: True})
        
    if request.method == "POST" :
        query = {key: value for key, value in request.POST.items() if value}
        songInsL = Song.objects.filter(**{f"{key}__icontains": value for key, value in query.items() if (key in INPUT_TEXTS)})
        
        filters = request.POST.getlist("filters")
        query["filters"] = filters
        filters_copy = filters.copy()
        if "islack" in filters_copy :
            songInsL = songInsL.filter(islack)
            filters_copy.remove("islack")
        songInsL = songInsL.filter(**{key: True for key in filters_copy})
        
        category = request.POST.get("category")
        if category != "all" :songInsL = filter_by_category(Song.objects.all(), category)

        songrange = request.POST.get("songrange")
        if songrange == "subeana" : songInsL = songInsL.filter(issubeana = True)
        if songrange == "xx" : songInsL = songInsL.filter(issubeana = False)
        
        jokerange = request.POST.get("jokerange")
        if jokerange == "off" : songInsL = songInsL.filter(isjoke = False)
        if jokerange == "only" : songInsL = songInsL.filter(isjoke = True)
    
    dataD["counter"] = f"{len(Song.objects.all())}曲中{len(songInsL)}曲表示しています。"
    dataD["query"] = query | query_select
    dataD["songInsL"] = songInsL.order_by("-posttime")
    return render(request, "subekashi/search.html", dataD)


def setting(request) :
    return render(request, "subekashi/setting.html")


def ad(request) :
    dataD = dict()
    check = ""
    urlForms = []
    for i in range(1, 4) :
        url = request.COOKIES.get(f"ad{i}") if request.COOKIES.get(f"ad{i}") else ""
        dataD[f"url{i}"] = url
        dataD[f"ad{i}"] = url
        check += url
        urlForms.append(url)
        
    dataD["sha256"] = sha256(check)
    
    if request.method == "POST" :
        checkPOST = ""
        urlForms = []
        adForms = []
        for i in range(1, 4) :
            urlForm = formatURL(request.POST.get(f"url{i}", ""))
            adForm = formatURL(request.POST.get(f"ad{i}", ""))
            sha256Form = request.POST.get("sha256")
            
            checkPOST += adForm
            urlForms.append(urlForm)
            adForms.append(adForm)
        
        if sha256Form != sha256(checkPOST) :
            dataD["error"] = "不正なパラメータが含まれています"
            return render(request, "subekashi/ad.html", dataD)
        
        for i, urlForm, adForm in zip(range(1, 4), urlForms, adForms) :
            if urlForm == adForm :
                continue
            
            adIns = Ad.objects.filter(url = adForm).first()
            if (adIns == None) and (adForm != "") :
                dataD["error"] = "内部エラーが発生しました"
                return render(request, "subekashi/ad.html", dataD)
            elif adForm != "" :
                adIns.dup -= 1
                adIns.save()
            
            if urlForm == "" :
                continue
        
            if not(isYouTubeLink(urlForm)) and (urlForm != "") :
                dataD["error"] = "YouTubeのURLを入力してください"
                dataD[f"ad{i}"] = ""
                dataD[f"url{i}"] = ""
                urlForms[i - 1] = ""
                dataD["sha256"] = sha256("".join(urlForms))
                return render(request, "subekashi/ad.html", dataD)
            
            adIns, isCreate = Ad.objects.get_or_create(url = urlForm)
            adIns.dup += 1
            adIns.save()
            if isCreate :
                sendDiscord(DSP_DISCORD_URL, f"{urlForm}, {adIns.id}")
        
        return redirect("subekashi:adpost")
                
    ads = set()
    for urlForm in urlForms :
        if urlForm == "" : 
            continue
        adIns = Ad.objects.filter(url = urlForm).first()
        if not adIns :
            continue
            
        ads.add(adIns)
    
    dataD["ads"] = list(ads)
    
    return render(request, "subekashi/ad.html", dataD)


def adpost(request) :
    return render(request, "subekashi/adpost.html")


def research(request) :
    return render(request, "subekashi/research.html")


def special(request) :
    images = ["default", "autumn", "cool", "rainbow", "spring", "summer", "winter", "Blues_r", "BuGn_r", "BuPu_r", "GnBu_r", "Greens_r", "OrRd_r", "Spectral_r"]
    detaD = {"images": images}
    return render(request, "subekashi/special.html", detaD)


def error(request) :
    return render(request, "subekashi/500.html")


def dev(request) :
    dataD = {"locked" : True}
    if request.method == "POST":
        password = request.POST.get("password")

        if password :
            if hashlib.sha256(password.encode()).hexdigest() == SHA256a :
                dataD["locked"] = False
        isgpt = request.GET.get("gpt")

        if isgpt :
            inp_gpt = request.POST.get("gpt")
            if inp_gpt :
                gpt_lines = inp_gpt.split("\n")[12:]
                gpt_lines = [i for i in gpt_lines if i[0] != "="]
                gpt_lines = sum(list(map(lambda i : re.split("、|。|？", i), gpt_lines)), [])
                gpt_lines = set(map(lambda i : re.sub("{|}|/|「|」|（|）|(|)|[ -¡]", "", i), gpt_lines))
                gpt_lines = [i for i in gpt_lines if (6 < len(i) < 22) and not(re.compile(r'[0-9a-zA-Z]+').search(i))]
                [Ai.objects.create(lyrics = i, genetype = "model").save() for i in set(gpt_lines)]

                dataD["locked"] = False
            
    return render(request, "subekashi/dev.html", dataD)


def github(request) :
    return redirect("https://github.com/izumin2000/subekashi")


def robots(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/robots.txt")


def sitemap(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/sitemap.xml")


def appleicon(request) :
    return redirect(f"{ROOT_DIR}/static/subekashi/image/apple-touch-icon.png")


class SongViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer


class AiViewSet(viewsets.ModelViewSet):
    queryset = Ai.objects.all()
    serializer_class = AiSerializer
    
    def create(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドCREATEは受け付けていません")
    
    def update(self, request, *args, **kwargs):
        if set(request.data.keys()) - {'score'}:
            raise serializers.ValidationError("フィールドscore以外の変更は受け付けていません")
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドDELETEは受け付けていません")


class AdViewSet(viewsets.ModelViewSet):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    
    def create(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドCREATEは受け付けていません")
    
    def update(self, request, *args, **kwargs):
        if set(request.data.keys()) - {'view', 'click'}:
            raise serializers.ValidationError("フィールドviewとフィールドclick以外の変更は受け付けていません")
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドDELETEは受け付けていません")
    

def clean(request) :
    result = management.call_command("clean")
    res = {"result" : result if result else "競合は発生していません"}
    return JsonResponse(json.dumps(res, ensure_ascii=False), safe=False)


def handle_404_error(request, exception=None):
    return render(request, 'subekashi/404.html', status=404)
    

def handle_500_error(request):
    error_msg = traceback.format_exc()
    sendDiscord(ERROR_DISCORD_URL, error_msg)
    return render(request, 'subekashi/500.html', status=500)