from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from config.settings import ROOT_URL
from config.local_settings import CONTACT_DISCORD_URL
from subekashi.forms import EditorReportForm
from subekashi.lib.discord import send_discord
from subekashi.lib.ip import get_ip
from subekashi.models import Editor


# 編集者のページの「報告」ボタンから、荒らしを管理者に報告する（#1291）
class EditorReportView(View):
    def dispatch(self, request, editor_id, *args, **kwargs):
        self.editor = Editor.get_or_none(editor_id)
        if self.editor is None:
            return render(request, 'subekashi/404.html', status=404)
        self.reporter_ip = get_ip(request)
        # 自分自身は報告できない
        if self.reporter_ip == self.editor.ip:
            return redirect('subekashi:editor', editor_id=self.editor.id)
        return super().dispatch(request, editor_id, *args, **kwargs)

    def get_base_context(self):
        return {
            "metatitle": f"{self.editor}を報告",
            "editor": self.editor,
        }

    def get(self, request, editor_id):
        return render(request, 'subekashi/editor_report.html', self.get_base_context())

    def post(self, request, editor_id):
        context = self.get_base_context()
        form = EditorReportForm(request.POST)

        if not form.is_valid():
            context["error"] = form.errors['reason'][0]
            context["reason"] = request.POST.get("reason", "")
            return render(request, 'subekashi/editor_report.html', context)

        reason = form.cleaned_data['reason']

        content = (
            f"荒らしの報告\n"
            f"理由：{reason}\n"
            f"報告された編集者：{ROOT_URL}/admin/subekashi/editor/{self.editor.id}/change/\n"
            f"報告した人のIP：{self.reporter_ip}\n"
        )
        is_ok = send_discord(CONTACT_DISCORD_URL, content)
        if not is_ok:
            context["error"] = "報告を送信できませんでした。時間をおいて再度お試しください。"
            context["reason"] = reason
            return render(request, 'subekashi/editor_report.html', context)

        return redirect(f"{reverse('subekashi:editor', args=[self.editor.id])}?toast=report")
