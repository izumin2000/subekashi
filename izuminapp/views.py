from django.shortcuts import render
import requests
from izuminapp.model import Oldjson, Player, Firstview

ABLE_API = False
API_URL = "https://earthmc-api.herokuapp.com/api/v1"
SAMPLE_TITLE = ["サンプル画像1", "サンプル画像2"]
SAMPLE_PLAYER = ["KANATA2000", "かなた"]

def root(request):
    inca_info = {}
    # return render(request, 'inca/inca.html', inca_info)
    return render(request, 'izuminapp/root.html')

def inca(request):
    inca_info = {}
    inca_info["clTitle"] = SAMPLE_TITLE
    inca_info["clPlayers"] = SAMPLE_PLAYER
    if ABLE_API :
        nations = requests.get(API_URL + "/nations/Inca_Empire")
        if (nations.status_code == 200) and ABLE_API :
            nations_info = dict(nations.json())
            inca_info.update(nations_info)
            # print(Oldjson.objects.all().count())
        else :
            inca_info["nodata"] = True
    else :
        inca_info["nodata"] = True


    return render(request, 'inca/inca.html', inca_info)