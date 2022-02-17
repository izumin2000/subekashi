from django.http import HttpResponse
from django.shortcuts import render, redirect
# from .models import Hoge

def root(request):
    return render(request, 'izuminapp/root.html')