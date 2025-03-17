from django.shortcuts import render


def discord(request):
    return render(request, 'subekashi/discord.html')