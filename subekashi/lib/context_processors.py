from config.settings import BASE_DIR
from subekashi.constants.constants import CONST_ERROR, ASIDE_PAGES
import json
import os

MAINTENANCE_JSON_PATH = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/maintenance.json')
VERSION_JSON_PATH = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/version.json')

def context_processors(request):
    if os.path.exists(VERSION_JSON_PATH):
        with open(VERSION_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            version = data.get("VERSION", CONST_ERROR)
    else:
        version = CONST_ERROR

    if os.path.exists(MAINTENANCE_JSON_PATH):
        with open(MAINTENANCE_JSON_PATH, "r", encoding="utf-8") as f:
            maintenance = json.load(f)
    else:
        maintenance = {}

    context = {
        "aside_pages": ASIDE_PAGES,
        "version": version,
        "is_maintenance": maintenance.get("IS_MAINTENANCE", False),
        "maintenance_message": maintenance.get("MAINTENANCE_MESSAGE", "<p>メンテナンス中です</p>"),
        "pc_menu_position": request.COOKIES.get("pc_menu_position", "header"),
    }

    return context
