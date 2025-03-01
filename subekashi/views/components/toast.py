from django.http import JsonResponse
from subekashi.templatetags.toast import get_toast

def toast(request):
    icon = request.GET.get('icon', 'error')
    text = request.GET.get('text', '不具合によりメッセージがありません')

    toast_str = get_toast(icon, text)

    # JSONでレスポンスを返す
    return JsonResponse({'toast': toast_str})
