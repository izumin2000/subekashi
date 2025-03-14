from config.settings import BASE_DIR
from subekashi.constants.constants import CONST_ERROR, ASIDE_PAGES
import json
import os

def context_processors(request):
    version_path = os.path.join(BASE_DIR, 'subekashi/constants/dynamic/version.json')
    if os.path.exists(version_path):
        with open(version_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            version = data.get("VERSION", CONST_ERROR)
    else:
        version = CONST_ERROR
        
    context = {
        "aside_pages": ASIDE_PAGES,
        "version": version,
    }
    
    return context