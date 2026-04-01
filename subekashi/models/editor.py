from django.db import models


# SongやAuthorを編集したユーザーのIPアドレスの情報
# 画面上では"全て{song_id}の所為です。"と表示される
class Editor(models.Model):
    ip = models.CharField(default = "", unique=True, max_length = 100)
    is_open = models.BooleanField(default = True)
    is_forced_open = models.BooleanField(default = False)

    def __str__(self):
        return f"全て{self.id}の所為です。"

    @classmethod
    def get_or_create_from_ip(cls, ip):
        editor, _ = cls.objects.get_or_create(ip=ip)
        return editor
