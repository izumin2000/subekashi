from django.db import models
from django.utils import timezone


SONGRANGE_CHOICES = (
    ("all", "全て"),
    ("subeana", "すべあな界隈曲のみ"),
    ("xx", "すべあな界隈曲以外"),
)


# 月次の統計スナップショット（毎月1日にstatsコマンドでsongrangeごとの累積値を保存する）
class Stats(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    songrange = models.CharField(default = "all", choices=SONGRANGE_CHOICES, max_length = 10)
    song_count = models.IntegerField(default = 0)
    total_view = models.IntegerField(default = 0)
    total_like = models.IntegerField(default = 0)
    total_authors = models.IntegerField(default = 0)
    total_imitateds = models.IntegerField(default = 0)
    create_time = models.DateTimeField(default = timezone.now)

    class Meta:
        ordering = ["year", "month", "songrange"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month", "songrange"], name="unique_stats_year_month_songrange"),
        ]

    def __str__(self):
        return f"{self.year}-{self.month:02d} ({self.songrange})"

    @classmethod
    def get_monthly_series(cls, songrange="all"):
        return cls.objects.filter(songrange=songrange).order_by("year", "month")
