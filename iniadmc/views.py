from django.shortcuts import render
from iniadmc.models import Info
from .serializer import InfoSerializer
from rest_framework import viewsets

def top(request) :
    ins_crowd, _ = Info.objects.get_or_create(name = "crowd", defaults = {"name" : "crowd", "value" : "low"})
    return render(request, 'iniadmc/top.html', {"crowd" : ins_crowd.value})

def change(request) :
    ins_crowd, _ = Info.objects.get_or_create(name = "crowd", defaults = {"name" : "crowd", "value" : "low"})
    ins_crowd.value = "high"
    ins_crowd.save()
    return render(request, 'iniadmc/top.html', {"crowd" : ins_crowd.value})



class InfoViewSet(viewsets.ModelViewSet):
    queryset = Info.objects.all()
    serializer_class = InfoSerializer