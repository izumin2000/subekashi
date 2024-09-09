from django.shortcuts import render
from config.settings import *

class RestrictIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        ban_path = os.path.join(BASE_DIR, 'subekashi/static/subekashi/md/ban.md')
        self.banL = []
        if os.path.exists(ban_path):
            with open(ban_path, 'r', encoding='utf-8') as file:
                ban_md = file.read()
                banL = ban_md.split("\n")
                self.banL = banL

    def __call__(self, request):
        # TODO IPアドレスを取得できる関数をlibで定義
        forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_addresses:
            ip_address = forwarded_addresses.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        if ip_address in self.banL and request.method in ['POST', 'PUT']:
            return render(request, 'subekashi/500.html', status=500)

        response = self.get_response(request)
        return response
