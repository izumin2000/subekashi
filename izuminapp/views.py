from django.shortcuts import render
import requests
# from .models import Hoge

ABLE_API = False
SAMPLE_TITLE = ["サンプル画像1", "サンプル画像2"]
SAMPLE_PLAYER = ["KANATA2000", "かなた"]

def root(request):
    return render(request, 'izuminapp/root.html')

def inca(request):
    inca_info = {}
    if ABLE_API :
        nations = requests.get("https://earthmc-api.herokuapp.com/nations/Inca_Empire")
        if (nations.status_code == 200) and ABLE_API :
            nations_info = dict(nations.json())
            inca_info.update(nations_info)
            inca_info["clTitle"] = SAMPLE_TITLE
            inca_info["clPlayers"] = SAMPLE_PLAYER
        else :
            inca_info["nodata"] = True
    else :
        inca_info["nodata"] = True


    return render(request, 'inca/inca.html', inca_info)