import secrets
from django.db import models


def generate_api_key():
    return secrets.token_urlsafe(32)


# 曲のAPI（登録・変更・削除、#973）をX-API-Keyヘッダーで利用するためのAPIキー
# 管理サイトでのみ発行する。nameは誰に発行したかを区別するための任意の名前
# is_activeをFalseにすると、キーを削除せずに利用を止められる
class ApiKey(models.Model):
    name = models.CharField(max_length=100, unique=True)
    key = models.CharField(max_length=64, unique=True, default=generate_api_key, editable=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
