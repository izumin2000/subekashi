import json
import os

from django.core.management.base import BaseCommand
from config.settings import BASE_DIR
from subekashi.constants.constants import CONST_ERROR
from subekashi.models import Word


class Command(BaseCommand):
    help = "subekashi/constants/dynamic/word.jsonから模倣単語候補をWordに一括登録する。"

    def handle(self, *args, **options):
        word_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/word.json')
        try:
            file = open(word_path, 'r', encoding='utf-8')
            entries = json.load(file)
            file.close()
        except (OSError, json.JSONDecodeError):
            self.stdout.write(self.style.ERROR(CONST_ERROR))
            return

        words = []
        for entry in entries:
            word = entry.get('word', '')
            hinshi = entry.get('hinshi', '')
            if not word or not hinshi:
                continue
            for candidate in entry.get('candidates', []):
                if candidate:
                    words.append(Word(word=word, hinshi=hinshi, candidate=candidate))

        Word.objects.bulk_create(words, ignore_conflicts=True)
        self.stdout.write(self.style.SUCCESS(f"新規Word候補数：{len(words)}"))
