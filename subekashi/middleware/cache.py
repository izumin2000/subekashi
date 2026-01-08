from datetime import datetime, timedelta, timezone
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date
from django.conf import settings
from subekashi.constants.constants import SHORT_TERM_COKKIE_AGE, LONG_TERM_COKKIE_AGE

class CacheControlMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        path = request.path

        if path.startswith(settings.STATIC_URL):
            max_age = LONG_TERM_COKKIE_AGE
        else:
            max_age = SHORT_TERM_COKKIE_AGE

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=max_age)

        response['Cache-Control'] = f'public, max-age={max_age}'
        response['Pragma'] = 'cache'
        response['Expires'] = http_date(expires_at.timestamp())

        return response