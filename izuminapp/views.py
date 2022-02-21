from django.http import HttpResponse
from django.shortcuts import render
import requests
# from .models import Hoge

def root(request):
    return render(request, 'izuminapp/root.html')

def inca(request):
    nations = requests.get("https://earthmc-api.herokuapp.com/nations/Inca_Empire")
    if nations.status_code == 200 :
        nations_info = dict(nations.json())
        print(nations_info["king"])
        inca_info = {"nodata": False}
    else :
        inca_info = {"nodata": True}
    return render(request, 'inca/inca.html', inca_info)