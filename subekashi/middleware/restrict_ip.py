from django.shortcuts import render
from config.settings import *

class RestrictIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        try:
            from subekashi.constants.dynamic.ban import BAN_LIST
        except :
            self.BAN_LIST = []
        else:
            self.BAN_LIST = BAN_LIST

    def __call__(self, request):
        # TODO IPアドレスを取得できる関数をlibで定義
        forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded_addresses:
            ip_address = forwarded_addresses.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        
        if ip_address in self.BAN_LIST:
            return render(request, 'subekashi/500.html', status=500)

        response = self.get_response(request)
        return response
