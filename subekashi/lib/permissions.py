import secrets
from django.conf import settings
from rest_framework import permissions
from subekashi.models import ApiKey


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


# X-API-Keyヘッダーの値が、管理サイトで発行した有効なApiKeyのkeyと一致するリクエストだけを許可する（#973）
# HasAPIKeyと違いキーは複数あり、is_activeをFalseにしたキーは拒否する
class HasIssuedAPIKey(permissions.BasePermission):
    message = "APIキーが正しくありません"

    def has_permission(self, request, view):
        received_key = request.headers.get("X-API-Key", "")
        if not received_key:
            return False

        api_key = ApiKey.objects.filter(key=received_key, is_active=True).first()
        # MySQLの照合順序は大文字小文字を区別しないため、取得したキーと改めて比較する
        return api_key is not None and secrets.compare_digest(received_key.encode(), api_key.key.encode())
