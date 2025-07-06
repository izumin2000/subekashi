from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date
from datetime import datetime, timedelta, timezone

class CacheControlMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=1800)
        response['Cache-Control'] = 'public, max-age=1800'
        response['Pragma'] = 'cache'
        response['Expires'] = http_date(expires_at.timestamp())
        return response