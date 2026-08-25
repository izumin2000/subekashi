from django.db import models


# janome+word2vecで算出した、ある単語と同じ品詞の類似語（模倣単語）候補
class Word(models.Model):
    word = models.CharField(max_length=100)
    hinshi = models.CharField(max_length=20)
    candidate = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['word', 'hinshi', 'candidate'], name='unique_word_hinshi_candidate'),
        ]
        indexes = [
            models.Index(fields=['word', 'hinshi']),
        ]

    def __str__(self):
        return f"{self.word}({self.hinshi}) -> {self.candidate}"

    @classmethod
    def get_candidates(cls, word, hinshi, limit=10):
        return list(
            cls.objects.filter(word=word, hinshi=hinshi)
            .exclude(candidate=word)
            .order_by('?')
            .values_list('candidate', flat=True)[:limit]
        )

    @classmethod
    def is_valid_candidate(cls, word, hinshi, candidate):
        return cls.objects.filter(word=word, hinshi=hinshi, candidate=candidate).exists()
