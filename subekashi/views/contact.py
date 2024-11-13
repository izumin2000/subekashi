from django.shortcuts import render
from subekashi.lib.discord import *
from subekashi.lib.ip import get_ip


def contact(request):
    dataD = {
        "metatitle" : "フィードバック",
    }
    
    if request.method == "POST" :
        contact = request.POST.get("contact")
        if not contact:
            return render(request, 'subekashi/500.html', status=500)
            
        content = f"フィードバック：{contact}\nIP：{get_ip(request)}"
        is_ok = sendDiscord(CONTACT_DISCORD_URL, content)
        if not is_ok:
            return render(request, 'subekashi/500.html', status=500)
        
    return render(request, 'subekashi/contact.html', dataD)