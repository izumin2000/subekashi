from django.http import JsonResponse
from subekashi.constants.constants import CONST_ERROR

def version_api(request):
    try:
        from subekashi.constants.dynamic.version import VERSION
        version = VERSION
    except:
        version = CONST_ERROR
    return JsonResponse({"version": version})