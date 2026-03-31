from django.db import models
from django.utils import timezone
from .song import Song
from .editor import Editor


# ユーザーによる曲や作者の変更を記録した情報
# changeは編集内容をマークダウンで記録する
class History(models.Model):
    CHOICES = (
        ("new", "新規作成"),
        ("edit", "編集"),
        ("delete", "削除申請"),
    )

    song = models.ForeignKey(Song, blank = True, null = True, on_delete = models.SET_NULL, related_name="histories")
    title = models.CharField(default = "", max_length = 100)
    history_type = models.CharField(default = "new", choices=CHOICES, max_length = 10)
    create_time = models.DateTimeField(default = timezone.now)
    changes = models.JSONField(null=True, blank=True, default=None)
    editor = models.ForeignKey(Editor, on_delete = models.CASCADE, related_name="histories")
