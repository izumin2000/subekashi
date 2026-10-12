import secrets
from django.conf import settings
from rest_framework import permissions


# X-API-Keyヘッダーの値がlocal_settings.pyのAPI_KEYと一致するリクエストだけを許可する（#925）
class HasAPIKey(permissions.BasePermission):
    message = "APIキーが正しくありません"

    def has_permission(self, request, view):
        # API_KEYが未設定（空文字列）の環境では、空のヘッダーと一致させないよう常に拒否する
        api_key = getattr(settings, "API_KEY", "")
        if not api_key:
            return False

        received_key = request.headers.get("X-API-Key", "")
        return secrets.compare_digest(received_key.encode(), api_key.encode())
