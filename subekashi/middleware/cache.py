from django.utils.deprecation import MiddlewareMixin

class CacheControlMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        return response