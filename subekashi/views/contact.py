from django.shortcuts import render
from django.views import View
from subekashi.forms import ContactForm
from subekashi.lib.discord import send_discord
from subekashi.lib.ip import get_ip
from subekashi.models import Contact
from config.local_settings import CONTACT_DISCORD_URL


class ContactView(View):
    def dispatch(self, request, *args, **kwargs):
        self.contact_qs = Contact.get_answered()
        return super().dispatch(request, *args, **kwargs)

    def get_base_context(self):
        return {
            "metatitle": "お問い合わせ",
            "contact_qs": self.contact_qs,
        }

    def get(self, request):
        return render(request, 'subekashi/contact.html', self.get_base_context())

    def post(self, request):
        context = self.get_base_context()
        form = ContactForm(request.POST)

        if not form.is_valid():
            context["result"] = "入力必須項目を入力してください。"
            return render(request, 'subekashi/contact.html', context)

        category = form.cleaned_data['category']
        detail = form.cleaned_data['detail']

        # discordに送信
        contact = f"種類：{category}\n\
            詳細：{detail}\n\
            IP：{get_ip(request)}\n\
        "
        is_ok = send_discord(CONTACT_DISCORD_URL, contact)
        if not is_ok:
            context["result"] = "内部エラーが発生しました。"
            return render(request, 'subekashi/contact.html', context)

        # okトーストを表示
        context["result"] = "ok"
        return render(request, 'subekashi/contact.html', context)
