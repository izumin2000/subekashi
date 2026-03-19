import re
import json
import os
from django.conf import settings
from django.template.response import TemplateResponse

MAINTENANCE_PATHS = [
    re.compile(r'^/songs/new/$'),
    re.compile(r'^/songs/\d+/edit/$'),
    re.compile(r'^/songs/\d+/delete/$'),
    re.compile(r'^/ai/result/$'),
    re.compile(r'^/ad/complete/$'),
]

MAINTENANCE_JSON_PATH = os.path.join(
    settings.BASE_DIR, 'subekashi/constants/dynamic/maintenance.json'
)


def _load_maintenance():
    with open(MAINTENANCE_JSON_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        data = _load_maintenance()
        if data.get('IS_MAINTENANCE', False):
            for pattern in MAINTENANCE_PATHS:
                if pattern.match(request.path):
                    response = TemplateResponse(request, 'subekashi/maintenance.html', {
                        'metatitle': 'メンテナンス中',
                    })
                    response.render()
                    return response
        return self.get_response(request)
