from django.shortcuts import render
from config.settings import *
from subekashi.lib.ip import get_ip

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
        ip = get_ip(request, False)
        if ip in self.BAN_LIST:
            return render(request, 'subekashi/500.html', status=500)

        response = self.get_response(request)
        return response
