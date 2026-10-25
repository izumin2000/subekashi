from django.db import models
from .song import Song


# すべあな界隈年表で曲が載っている行。timelineコマンドで保存し、曲のページの「年表で見る」ボタンに使う（#1269）
# 複数の行に一致する曲は、カテゴリ・プレラと同じく最初の行にする
class SongTimeline(models.Model):
    song = models.OneToOneField(Song, on_delete=models.CASCADE, related_name="timeline")
    year = models.IntegerField()
    # シートのID（URLのgid）
    sheet_id = models.IntegerField()
    row = models.IntegerField()
    # 歌詞列にこの曲のページのURLが書かれているか
    has_lyrics_url = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.year}年{self.row}行目"
