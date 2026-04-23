from django.shortcuts import render
from django.views import View
from config.local_settings import CONTACT_DISCORD_URL
from subekashi.lib.discord import send_discord
from subekashi.lib.ip import get_ip


class lilyrikuView(View):
    def get(self, request):
        url = request.GET.get("url", "")
        if url:
            send_discord(CONTACT_DISCORD_URL, f"リリリクオススメ:{url}")
            send_discord(CONTACT_DISCORD_URL, get_ip(request))
        
        context = {
            "metatitle": "すべかしオリキャラ「リリ」と「リク」のご紹介",
        }
        return render(request, 'article/lilyriku.html', context)