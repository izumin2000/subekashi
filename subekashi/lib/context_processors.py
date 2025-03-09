from subekashi.constants.constants import ASIDE_PAGES

def context_processors(request):
    context = {
        "aside_pages": ASIDE_PAGES,
    }
    
    return context