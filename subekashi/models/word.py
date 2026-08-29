import random

from django.db import models


# janome+word2vecで算出した、ある単語と同じ品詞・活用形の類似語（模倣単語）候補
class Word(models.Model):
    word = models.CharField(max_length=100)
    hinshi = models.CharField(max_length=20)
    # 動詞・形容詞は活用形（infl_form）、名詞は品詞細分類（part_of_speechのフル文字列）、
    # それ以外は空文字列。word無しでhinshi・katsuyouだけで候補を横断的に絞り込んでも
    # 文法的に破綻しにくくするために使う（SubeteJanomeNoSeidesu側と規約を合わせる必要がある）
    katsuyou = models.CharField(max_length=50, default="", blank=True)
    candidate = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['word', 'hinshi', 'katsuyou', 'candidate'], name='unique_word_hinshi_candidate'),
            models.CheckConstraint(check=~models.Q(word=models.F('candidate')), name='word_not_equal_candidate'),
        ]
        indexes = [
            models.Index(fields=['word', 'hinshi']),
            models.Index(fields=['hinshi', 'katsuyou']),
        ]

    def __str__(self):
        return f"{self.word}({self.hinshi}) -> {self.candidate}"

    @classmethod
    def get_candidates(cls, word, hinshi, katsuyou, limit=10):
        # 元の単語（word）は問わず、品詞（hinshi）・活用形（katsuyou）が一致する
        # 候補を横断的に対象にする。
        # order_by('?')（SQLの ORDER BY RANDOM()）はDB側でのフルソートになり
        # コストが増えるため使わない。hinshi・katsuyouで絞り込んだ（インデックス使用）
        # 結果をPython側でシャッフルする
        candidates = list(
            cls.objects.filter(hinshi=hinshi, katsuyou=katsuyou)
            .exclude(candidate=word)
            .values_list('candidate', flat=True)
            .distinct()
        )
        random.shuffle(candidates)
        return candidates[:limit]

    @classmethod
    def is_valid_candidate(cls, word, hinshi, katsuyou, candidate):
        if word == candidate:
            return False
        return cls.objects.filter(hinshi=hinshi, katsuyou=katsuyou, candidate=candidate).exists()
