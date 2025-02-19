from django.urls import resolve
from subekashi.constants.constants import *

def context_processors(request):
    context = {
        "aside_pages": ASIDE_PAGES,
    }
    return context