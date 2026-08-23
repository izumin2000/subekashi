from django.shortcuts import render
from django.views import View
from subekashi.models import Ai
from subekashi.lib.lyric_tokenizer import tokenize_ai_instances


class AiView(View):
    def get(self, request):
        context = {
            "metatitle": "歌詞生成",
            "show_janome_notice": request.COOKIES.get("show_janome_notice", "on") == "on",
            "bestInsL": tokenize_ai_instances(Ai.get_high_scored_model()),
        }
        return render(request, "subekashi/ai.html", context)
