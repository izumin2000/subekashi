from cgitb import reset
from sys import platlibdir
from turtle import title
from django.shortcuts import render
from izuminapp.forms import FirstviewForm
from izuminapp.model import Oldjson, Player, Firstview, Siteinfo
import requests
import datetime

API_URL = "https://earthmc-api.herokuapp.com/api/v1"
NUMBER_OF_FIRSTVIEWS = 5

def root(request):
    return render(request, 'izuminapp/root.html')

def inca(request):
    inca_info = {}
    firstviews = Firstview.objects.order_by('?')[:min(Firstview.objects.count(), NUMBER_OF_FIRSTVIEWS)]
    firstviews = list(firstviews.values())
    inca_info["images"] = [d.get('image') for d in firstviews]
    inca_info["clTitle"] = [d.get('title') for d in firstviews]
    inca_info["clPlayers"] = [d.get('player') for d in firstviews]

    try :
        nations = requests.get(API_URL + "/nations/Inca_Empire")
    except Exception :      # ProxyErrorなら
        inca_info["nodata"] = True
    else :
        if (nations.status_code == 200) :
            nations_info = dict(nations.json())
            inca_info.update(nations_info)
            # print(Oldjson.objects.all().count())
        else :
            inca_info["nodata"] = True

    return render(request, 'inca/inca.html', inca_info)

def applyimage(request) :
    result = {}
    if request.method == 'POST':
        newImage = request.FILES.get("image")
        newtitle = request.POST["title"]
        newPlayer = request.POST["player"]
        firstview = Firstview.objects.create(image = newImage, title = newtitle, player = newPlayer)
        firstview.save()
        result["title"] = newtitle
    else :
        result["title"] = "upload images..."

    form = FirstviewForm()
    result["form"] = form
    return render(request, 'inca/applyimage.html', result)