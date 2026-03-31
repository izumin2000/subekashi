from django.db import models


# すべかしDSPに登録された曲の情報
class Ad(models.Model):
    CHOICES = (
        ("still", "未審査"),
        ("pass", "公開中"),
        ("fail", "未通過"),
    )
    url = models.CharField(default = "", max_length = 100)
    view = models.IntegerField(default = 0)
    click = models.IntegerField(default = 0)
    dup = models.IntegerField(default = 0)
    status = models.CharField(default = "still", choices=CHOICES, max_length=10)

    def __str__(self):
        return self.url
