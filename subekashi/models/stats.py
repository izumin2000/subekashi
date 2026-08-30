from django.db import models
from django.utils import timezone


# 月次の統計スナップショット（毎月1日にstatsコマンドで累積値を保存する）
class Stats(models.Model):
    year = models.IntegerField()
    month = models.IntegerField()
    song_count = models.IntegerField(default = 0)
    total_view = models.IntegerField(default = 0)
    total_like = models.IntegerField(default = 0)
    total_authors = models.IntegerField(default = 0)
    total_imitateds = models.IntegerField(default = 0)
    create_time = models.DateTimeField(default = timezone.now)

    class Meta:
        ordering = ["year", "month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="unique_stats_year_month"),
        ]

    def __str__(self):
        return f"{self.year}-{self.month:02d}"

    @classmethod
    def get_monthly_series(cls):
        return cls.objects.order_by("year", "month")
