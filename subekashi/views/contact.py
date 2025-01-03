from django.shortcuts import render
from subekashi.lib.discord import *
from subekashi.lib.ip import get_ip
from subekashi.models import Contact


def contact(request):
    dataD = {
        "metatitle" : "お問い合わせ",
    }
    
    contact_qs = Contact.objects.exclude(answer = "").order_by("-id")
    dataD["contact_qs"] = contact_qs
    
    if request.method == "POST" :
        contact_type = request.POST.get("contact-type")
        detail = request.POST.get("detail")
        if (not contact_type) or (not detail):
            dataD["result"] = "入力必須項目を入力してください。"
            return render(request, 'subekashi/contact.html', dataD)

        contact = f"種類：{contact_type}\n\
        詳細：{detail}\n\
        IP：{get_ip(request)}"
        is_ok = sendDiscord(CONTACT_DISCORD_URL, contact)
        if not is_ok:
            dataD["result"] = "内部エラーが発生しました。"
            return render(request, 'subekashi/contact.html', dataD)
        
        dataD["result"] = "ok"

    return render(request, 'subekashi/contact.html', dataD)