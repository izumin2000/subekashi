from django.db import models


# プレミアラッシュ（プレラ）。すべあな界隈年表のプ列からtimelineコマンドで登録し、ユーザーは登録・編集できない（#1064）
class Prush(models.Model):
    name = models.CharField(unique=True, max_length=255)

    def __str__(self):
        return self.name
