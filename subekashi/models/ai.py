from django.db import models


# 正常に狂うのです。が生成した歌詞の情報
class Ai(models.Model):
    lyrics = models.CharField(default = "", max_length = 100)
    score = models.IntegerField(default = 0)
    genetype = models.CharField(default = "", max_length = 100)

    def __str__(self):
        return self.lyrics

    @classmethod
    def get_top_scored(cls):
        return cls.objects.filter(score=5)
