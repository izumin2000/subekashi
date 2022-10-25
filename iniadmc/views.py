from django.shortcuts import render

from iniadmc.models import Info

def top(request) :
    ins_crowd, _ = Info.objects.get_or_create(name = "crowd", defaults = {"name" : "crowd", "value" : "low"})
    return render(request, 'iniadmc/top.html', {"crowd" : ins_crowd.value})