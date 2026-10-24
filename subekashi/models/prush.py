from django.db import models


# プレミアラッシュ（プレラ）。すべあな界隈年表のプ列からtimelineコマンドで登録し、ユーザーは登録・編集できない（#1064）
class Prush(models.Model):
    name = models.CharField(unique=True, max_length=255)
    # 年表でこのプレラが最初に出てくる行の日付。曲の検索の選択肢を新しい順に並べ、年ごとに分けるのに使う
    date = models.DateField(blank=True, null=True, default=None)

    def __str__(self):
        return self.name
