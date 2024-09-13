from django.core.management.base import BaseCommand
from config.settings import *
from subekashi.models import Ai
from subekashi.constants.view import *
import re
import requests
import os


class Command(BaseCommand):
    help = "Ai関連のコマンド。-cがあると未評価数をカウントし、無いとsubekashi/constants/dynamic/gpt.txtからAiに生成した歌詞を追加する。"

    def handle(self, *args, **options) :
        if options['c']:
            ai_json = requests.get("https://lyrics.imicomweb.com/api/ai/").json()
            count = len(["" for ai in ai_json if ai["score"] == 0])
            self.stdout.write(self.style.SUCCESS(f"未評価数：{count}"))
            return
            
        try:
            gpt_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/gpt.txt')
            file = open(gpt_path, 'r', encoding='utf-8')
            gpt_text = file.read()
            file.close()
        except :
            self.stdout.write(self.style.ERROR(CONST_ERROR))
            return
        
        gpt_lines = re.split("、|。|\?|？|\r\n|\n", gpt_text)
        gpt_lines = set([i for i in gpt_lines if (6 < len(i) < 22)])
        ais = [Ai(lyrics=i, genetype="model") for i in gpt_lines]
        Ai.objects.bulk_create(ais)
        self.stdout.write(self.style.SUCCESS(f"新規Ai数：{len(ais)}"))
        return
        
    def add_arguments(self, parser):
        parser.add_argument('-c', required=False, action='store_true')