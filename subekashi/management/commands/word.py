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
            with open(word_path, 'r', encoding='utf-8') as file:
                entries = json.load(file)
        except (OSError, json.JSONDecodeError):
            self.stdout.write(self.style.ERROR(CONST_ERROR))
            return

        if not isinstance(entries, list):
            self.stdout.write(self.style.ERROR(CONST_ERROR))
            return

        words = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            word = entry.get('word', '')
            hinshi = entry.get('hinshi', '')
            katsuyou = entry.get('katsuyou') or ''
            candidates = entry.get('candidates', [])
            if not word or not hinshi or not isinstance(candidates, list):
                continue
            for candidate in candidates:
                if candidate and isinstance(candidate, str):
                    words.append(Word(word=word, hinshi=hinshi, katsuyou=katsuyou, candidate=candidate))

        count_before = Word.objects.count()
        Word.objects.bulk_create(words, ignore_conflicts=True)
        created_count = Word.objects.count() - count_before
        self.stdout.write(self.style.SUCCESS(f"新規Word候補数：{created_count}"))
