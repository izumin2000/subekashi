import json
import os
from django.shortcuts import render
from config.settings import *
from subekashi.lib.ip import get_ip

class RestrictIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        try:
            ban_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/ban.json')
            with open(ban_path, "r", encoding="utf-8") as f:
                self.BAN_LIST = json.load(f)
        except:
            self.BAN_LIST = []

    def __call__(self, request):
        ip = get_ip(request, raw=True)
        if ip in self.BAN_LIST:
            return render(request, 'subekashi/500.html', status=500)

        response = self.get_response(request)
        return response
