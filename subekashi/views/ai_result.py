from django.shortcuts import render
from django.views import View
from subekashi.models import Ai
from subekashi.lib.discord import send_discord
from config.local_settings import ERROR_DISCORD_URL


class AiResultView(View):
    def get(self, request):
        context = {
            "metatitle": "歌詞の生成結果",
        }

        aiIns = Ai.get_unscored_model()
        if not aiIns.exists():
            try:
                from subekashi.constants.dynamic.ai import SEND_DISCORD_AI_RESULT
            except ImportError:
                SEND_DISCORD_AI_RESULT = True

            if SEND_DISCORD_AI_RESULT:
                send_discord(ERROR_DISCORD_URL, "aiInsのデータがありません。")
            aiIns = Ai.get_all_model()
        context["aiInsL"] = aiIns.order_by('?')[:25]
        return render(request, "subekashi/ai_result.html", context)
