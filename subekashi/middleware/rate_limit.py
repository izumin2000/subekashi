from django_ratelimit.exceptions import Ratelimited
from django.http import JsonResponse

class RatelimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            response = self.get_response(request)
        except Ratelimited:
            response = JsonResponse({'error': 'Rate limit exceeded'}, status=429)
        return response
