from django.db import models


# 全て蛇の目の所為です。が作成した歌詞の情報
class Ai(models.Model):
    # 単語入れ替え（janome）で作成されたAiレコードのgenetype。
    # レガシーのGPTインポート（"model"）は廃止済みのため、現在使われるのはこれのみ
    GENETYPE_JANOME = "janome"

    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    genetype = models.CharField(default = "", max_length = 100)

    def __str__(self):
        return self.lyrics

    @classmethod
    def get_top_scored(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME, score=5)

    @classmethod
    def get_high_scored_janome(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME, score=5).order_by('?')[:300]

    @classmethod
    def get_unscored_janome(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME, score=0)

    @classmethod
    def get_all_janome(cls):
        return cls.objects.filter(genetype=cls.GENETYPE_JANOME)
