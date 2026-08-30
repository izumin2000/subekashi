from django.shortcuts import render
from django.views import View
from subekashi.models import Ai


class AiView(View):
    def get(self, request):
        context = {
            "metatitle": "歌詞作成",
            "show_janome_notice": request.COOKIES.get("show_janome_notice", "on") == "on",
            "bestInsL": Ai.get_high_scored_janome(),
        }
        return render(request, "subekashi/ai.html", context)
