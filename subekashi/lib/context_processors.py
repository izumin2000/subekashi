from django.urls import resolve
from subekashi.constants.constants import *
from subekashi.constants.dynamic.version import VERSION

def context_processors(request):
    try:
        from subekashi.constants.dynamic.version import VERSION
        version = VERSION
    except:
        version = CONST_ERROR
        
    context = {
        "aside_pages": ASIDE_PAGES,
        "version": version,
    }
    
    return context