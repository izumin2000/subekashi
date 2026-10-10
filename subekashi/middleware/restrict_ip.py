from django.shortcuts import render
from config.settings import *
from subekashi.lib.ip import get_ip, log_client_ip_check, log_forwarded_ip_mismatch

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
        log_forwarded_ip_mismatch(request)
        log_client_ip_check(request)
        ip = get_ip(request, raw=True)
        if ip in self.BAN_LIST:
            return render(request, 'subekashi/500.html', status=500)

        response = self.get_response(request)
        return response
