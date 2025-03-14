from django.http import JsonResponse
from config.settings import BASE_DIR
import json
import os

def version_api(request):
    version_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/version.json')
    if os.path.exists(version_path):
        with open(version_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return JsonResponse(data)
    else:
        return JsonResponse({})