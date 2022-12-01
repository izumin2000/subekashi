from django.shortcuts import render
from iniadmc.models import Wait
from .serializer import WaitSerializer
from rest_framework import viewsets
from config.settings import BASE_DIR as BASE_DIRpath

def top(request) :
    if not len(Wait.objects.all()) :
        ins_wait = Wait.objects.create()
        ins_wait.minutes = 0
        ins_wait.save()
    ins_wait = Wait.objects.first()
    BASE_DIR = str(BASE_DIRpath)
    if "C:" in BASE_DIR :
        BASE_DIR = "http://iniadmc.localhost:8000"
    elif "app" in BASE_DIR :
        BASE_DIR = ""
    return render(request, 'iniadmc/top.html', {"minutes" : ins_wait.minutes, "BASE_DIR" : BASE_DIR})

def change(request) :
    if not len(Wait.objects.all()) :
        ins_wait = Wait.objects.create()
        ins_wait.minutes = 0
        ins_wait.save()
    ins_wait = Wait.objects.first()
    if request.method == "POST":
        inp_minutes = request.POST.get("minutes")
        ins_wait.minutes = inp_minutes
        ins_wait.save()
    
    return render(request, 'iniadmc/change.html', {"minutes" : ins_wait.minutes})



class WaitViewSet(viewsets.ModelViewSet):
    queryset = Wait.objects.all()
    serializer_class = WaitSerializer