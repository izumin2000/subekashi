from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from config.settings import ROOT_URL
from config.local_settings import CONTACT_DISCORD_URL
from subekashi.forms import EditorReportForm
from subekashi.lib.discord import send_discord
from subekashi.lib.ip import get_ip
from subekashi.models import Editor, History

# 履歴から報告したあとに戻るページ（next）が無い・安全でないときに戻るページ
DEFAULT_NEXT_URL = "/histories/"


# 戻り先のURLに、報告したことを伝えるトーストのクエリを付ける。既にあるtoastは置き換える
def add_report_toast(url):
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key != "toast"]
    query.append(("toast", "report"))
    return urlunsplit(parts._replace(query=urlencode(query)))


# 荒らしを管理者に報告する（#1291、#1294）
# 報告された編集者（self.editor）の決め方と戻り先は、サブクラスで実装する
class BaseEditorReportView(View):
    history = None

    def dispatch(self, request, *args, **kwargs):
        self.editor = self.find_editor(**kwargs)
        if self.editor is None:
            return render(request, 'subekashi/404.html', status=404)
        self.reporter_ip = get_ip(request)
        # 自分自身は報告できない
        if self.reporter_ip == self.editor.ip:
            return redirect(self.get_back_url(request))
        return super().dispatch(request, *args, **kwargs)

    def build_discord_text(self, reason):
        lines = [
            "荒らしの報告",
            f"理由：{reason}",
            f"報告された編集者：{ROOT_URL}/admin/subekashi/editor/{self.editor.id}/change/",
        ]
        if self.history:
            lines.append(f"報告された編集：{ROOT_URL}/admin/subekashi/history/{self.history.id}/change/")
        lines.append(f"報告した人のIP：{self.reporter_ip}")
        return "\n".join(lines) + "\n"

    def get(self, request, **kwargs):
        return render(request, 'subekashi/editor_report.html', self.get_context(request))

    def post(self, request, **kwargs):
        context = self.get_context(request)
        form = EditorReportForm(request.POST)

        if not form.is_valid():
            context["error"] = form.errors['reason'][0]
            context["reason"] = request.POST.get("reason", "")
            return render(request, 'subekashi/editor_report.html', context)

        reason = form.cleaned_data['reason']

        is_ok = send_discord(CONTACT_DISCORD_URL, self.build_discord_text(reason))
        if not is_ok:
            context["error"] = "報告を送信できませんでした。時間をおいて再度お試しください。"
            context["reason"] = reason
            return render(request, 'subekashi/editor_report.html', context)

        return redirect(add_report_toast(self.get_back_url(request)))


# 編集者のページの「報告」ボタンから報告する（#1291）
class EditorReportView(BaseEditorReportView):
    def find_editor(self, editor_id):
        return Editor.get_or_none(editor_id)

    def get_back_url(self, request):
        return reverse('subekashi:editor', args=[self.editor.id])

    def get_context(self, request):
        return {
            "metatitle": f"{self.editor}を報告",
            "heading": f"{self.editor}を報告",
            "form_action": reverse('subekashi:editor_report', args=[self.editor.id]),
            "back_url": self.get_back_url(request),
        }


# 履歴一覧・曲の履歴の「編集者: 非公開」の「報告」から、その履歴の編集者を報告する（#1294）
# 編集者のIDが画面・URLに出ると、同じIDの履歴どうしが同じ非公開の編集者のものだと分かってしまう
# （APIが非公開の編集者をnullにするのは、これを防ぐため）。そのため履歴から編集者を引き、編集者のIDを画面に出さない
class HistoryReportView(BaseEditorReportView):
    def find_editor(self, history_id):
        self.history = History.objects.select_related("editor").filter(pk=history_id).first()
        return self.history.editor if self.history else None

    # 報告を始めたページ。他のサイトなどへ飛ばされないよう、このサイトのURLだけを受け付ける
    def get_back_url(self, request):
        next_url = request.POST.get("next") or request.GET.get("next") or ""
        allowed = url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure())
        return next_url if allowed else DEFAULT_NEXT_URL

    def get_context(self, request):
        back_url = self.get_back_url(request)
        return {
            "metatitle": "編集を報告",
            "heading": "編集を報告",
            "form_action": reverse('subekashi:history_report', args=[self.history.id]),
            "back_url": back_url,
            "next_url": back_url,
            "history": self.history,
        }
