from django.shortcuts import render
from django.views import View
from subekashi.models import Ai


class AiView(View):
    def get(self, request):
        context = {
            "metatitle": "歌詞生成",
            "show_janome_notice": request.COOKIES.get("show_janome_notice", "True") == "True",
            "bestInsL": Ai.get_high_scored_model(),
        }
        return render(request, "subekashi/ai.html", context)
