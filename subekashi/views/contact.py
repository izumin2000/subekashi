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
        reply = request.POST.get("reply")
        
        # 選択肢が掲載拒否の場合、連絡先が空かどうか
        if (contact_type == "掲載拒否") and (not reply):
            dataD["result"] = "本人のアカウントかどうかの確認のため、連絡先の項目が必須になります。"
            return render(request, 'subekashi/contact.html', dataD)
        
        # 選択肢か詳細が空なら
        if (not contact_type) or (not detail):
            dataD["result"] = "入力必須項目を入力してください。"
            return render(request, 'subekashi/contact.html', dataD)

        # discordに送信
        contact = f"種類：{contact_type}\n\
            詳細：{detail}\n\
            {('連絡先: ' + reply) if reply else ''}\n\
            IP：{get_ip(request)}\n\
        "
        is_ok = send_discord(CONTACT_DISCORD_URL, contact)
        if not is_ok:
            dataD["result"] = "内部エラーが発生しました。"
            return render(request, 'subekashi/contact.html', dataD)
        
        # okトーストを表示
        dataD["result"] = "ok"

    return render(request, 'subekashi/contact.html', dataD)