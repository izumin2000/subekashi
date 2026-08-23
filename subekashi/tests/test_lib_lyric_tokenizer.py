"""
lib/lyric_tokenizer.py のテスト

歌詞の単語分割と、Word候補が存在する単語のみを
is_replaceable=True としてマークする処理を検証する。
"""
from django.test import TestCase
from subekashi.models import Ai, Word
from subekashi.lib.lyric_tokenizer import tokenize_ai_instances, tokenize_lyrics_with_index


class TokenizeLyricsWithIndexTest(TestCase):
    """tokenize_lyrics_with_index() のテスト"""

    def test_splits_into_surface_and_hinshi(self):
        tokens = tokenize_lyrics_with_index("私は走る")

        surfaces = [t["surface"] for t in tokens]
        self.assertEqual(surfaces, ["私", "は", "走る"])

    def test_assigns_sequential_index(self):
        tokens = tokenize_lyrics_with_index("私は走る")

        self.assertEqual([t["index"] for t in tokens], [0, 1, 2])

    def test_hinshi_is_top_level_category(self):
        tokens = tokenize_lyrics_with_index("私は走る")

        by_surface = {t["surface"]: t["hinshi"] for t in tokens}
        self.assertEqual(by_surface["私"], "名詞")
        self.assertEqual(by_surface["は"], "助詞")
        self.assertEqual(by_surface["走る"], "動詞")


class TokenizeAiInstancesTest(TestCase):
    """tokenize_ai_instances() のテスト"""

    def test_marks_word_with_existing_candidate_as_replaceable(self):
        Word.objects.create(word="走る", hinshi="動詞", candidate="駆ける")
        ai = Ai.objects.create(lyrics="私は走る", score=5, genetype="model")

        result = tokenize_ai_instances(Ai.objects.filter(pk=ai.pk))

        tokens = {t["surface"]: t for t in result[0]["tokens"]}
        self.assertTrue(tokens["走る"]["is_replaceable"])

    def test_word_without_candidate_is_not_replaceable(self):
        ai = Ai.objects.create(lyrics="私は走る", score=5, genetype="model")

        result = tokenize_ai_instances(Ai.objects.filter(pk=ai.pk))

        tokens = {t["surface"]: t for t in result[0]["tokens"]}
        self.assertFalse(tokens["私"]["is_replaceable"])
        self.assertFalse(tokens["走る"]["is_replaceable"])

    def test_particle_is_never_replaceable_even_with_matching_word_row(self):
        # 助詞は置き換え対象品詞ではないため、同じ表記のWordがあっても対象外
        Word.objects.create(word="は", hinshi="助詞", candidate="が")
        ai = Ai.objects.create(lyrics="私は走る", score=5, genetype="model")

        result = tokenize_ai_instances(Ai.objects.filter(pk=ai.pk))

        tokens = {t["surface"]: t for t in result[0]["tokens"]}
        self.assertFalse(tokens["は"]["is_replaceable"])

    def test_candidate_for_different_hinshi_does_not_leak(self):
        # 同じ表記でも品詞が違うWordの候補は対象外（word__in の絞り込み後に
        # (word, hinshi) の組で厳密に一致させているかを確認する）
        Word.objects.create(word="走る", hinshi="名詞", candidate="ランニング")
        ai = Ai.objects.create(lyrics="私は走る", score=5, genetype="model")

        result = tokenize_ai_instances(Ai.objects.filter(pk=ai.pk))

        tokens = {t["surface"]: t for t in result[0]["tokens"]}
        self.assertFalse(tokens["走る"]["is_replaceable"])

    def test_result_contains_id_and_lyrics(self):
        ai = Ai.objects.create(lyrics="私は走る", score=5, genetype="model")

        result = tokenize_ai_instances(Ai.objects.filter(pk=ai.pk))

        self.assertEqual(result[0]["id"], ai.id)
        self.assertEqual(result[0]["lyrics"], "私は走る")

    def test_empty_queryset_returns_empty_list(self):
        result = tokenize_ai_instances(Ai.objects.none())

        self.assertEqual(result, [])
