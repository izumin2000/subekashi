from django.shortcuts import render
from subekashi.lib.ip import get_ip
from subekashi.models import Editor


def setting(request):
    ip = get_ip(request)
    editor, _ = Editor.objects.get_or_create(ip = ip)
    dataD = {
        "metatitle": "設定",
        "editor": editor,
    }
    return render(request, "subekashi/setting.html", dataD)