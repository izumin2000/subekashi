from django.shortcuts import render
from config.settings import *
from subekashi.models import *
from subekashi.lib.url import *
from subekashi.lib.filter import *


def search(request) :
    dataD = {
        "metatitle" : "一覧と検索",
    }
    query = {}
    query_select = {}
    
    songInsL = Song.objects.all()  
    if request.method == "GET" :
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
        # TODO 要リファクタリング
        try:
            if filter == "islack" : songInsL = songInsL.filter(islack)
            elif filter : songInsL = songInsL.filter(**{filter: True})
        except:
            pass
        
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