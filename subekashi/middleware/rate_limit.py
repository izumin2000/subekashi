from django_ratelimit.exceptions import Ratelimited
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

# @ratelimit(block=True)が送出するRatelimitedはPermissionDeniedのサブクラスで、ミドルウェアの__call__に届く前に403のレスポンスになるため、
# ビューの例外を受け取るprocess_exceptionで429にする（#1187）
class RatelimitMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        if not isinstance(exception, Ratelimited):
            return None

        response = JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        # 制限はすべて秒単位（2回/秒）のため、1秒後に再試行させる
        response['Retry-After'] = '1'
        response['Cache-Control'] = 'no-store'
        return response
