from django.shortcuts import render
from iniadmc.models import Wait
from .serializer import WaitSerializer
from rest_framework import viewsets

def top(request) :
    ins_wait = Wait.objects.get(id=0)
    return render(request, 'iniadmc/top.html', {"minutes" : ins_wait.minutes})

def change(request) :
    ins_wait, _ = Wait.objects.get_or_create(minutes = 0, defaults = {"minutes" : 0})
    if request.method == "POST":
        inp_minutes = request.POST.get("minutes")
        ins_wait.minutes = inp_minutes
        ins_wait.save()
    
    return render(request, 'iniadmc/change.html', {"minutes" : ins_wait.minutes})



class WaitViewSet(viewsets.ModelViewSet):
    queryset = Wait.objects.all()
    serializer_class = WaitSerializer