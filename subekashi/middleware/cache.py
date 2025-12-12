from datetime import datetime, timedelta, timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date
from django.conf import settings

class CacheControlMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        path = request.path

        # 静的ファイルの場合は30日でそれ以外は30分
        if path.startswith(settings.STATIC_URL):
            max_age = 30 * 24 * 60 * 60
        else:
            max_age = 1800

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_age)

        response['Cache-Control'] = f'public, max-age={max_age}'
        response['Pragma'] = 'cache'
        response['Expires'] = http_date(expires_at.timestamp())

        return response