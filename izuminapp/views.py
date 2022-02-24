from django.shortcuts import render
import requests
from izuminapp.model import Oldjson, Player, Firstview

<<<<<<< HEAD
ABLE_API = False
=======
>>>>>>> 13d566d7f4f64a38cefdb4e1eb8da468c22b4f73
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