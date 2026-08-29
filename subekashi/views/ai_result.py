from django.shortcuts import render
from django.views import View
from subekashi.models import Ai
from subekashi.lib.lyric_tokenizer import tokenize_ai_instances


class AiResultView(View):
    def get(self, request):
        context = {
            "metatitle": "歌詞の作成結果",
        }

        aiIns = Ai.get_unscored_janome()
        if not aiIns.exists():
            # 未評価のjanomeレコードが尽きても、単語入れ替えの元になる歌詞が
            # 表示され続けるよう、評価済みも含めた全janomeレコードにフォールバックする
            aiIns = Ai.get_all_janome()
        context["aiInsL"] = tokenize_ai_instances(aiIns.order_by('?')[:25])
        return render(request, "subekashi/ai_result.html", context)
