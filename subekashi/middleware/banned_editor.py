from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import parse_qsl, urlencode, urlsplit
from subekashi.constants.constants import BANNED_ERROR
from subekashi.lib.ip import get_ip
from subekashi.models import Editor

# ページの読み取りは、BANされた編集者もできる
READ_METHODS = ("GET", "HEAD", "OPTIONS", "TRACE")

# 検索条件のCookieを保存するだけで、DBに保存せず、検索結果のページを返すPOST。ページの読み取りとして許可する
READ_ONLY_POSTS = ("/songs/",)

# 戻し先のページで、別のトーストを出してしまうクエリ
TOAST_QUERY_KEYS = ("toast", "name_unified")


# Editor.is_bannedの編集者が、ページの読み取り以外のリクエスト（POST・PUT・PATCH・DELETE）をできないようにする（#1281）
# ビューごとに判定すると新しいビューで漏れるため、ミドルウェアでまとめて判定する
# - /api/: JSONで403を返す（JSの呼び出し側が失敗として扱う）
# - フォーム: 送信したフォームのあるページ（Referer）に戻してトーストを表示する（base.js）。戻れない場合は500のページを表示する
class BannedEditorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self.is_blocked(request):
            return self.blocked_response(request)
        return self.get_response(request)

    def is_blocked(self, request):
        if request.method in READ_METHODS:
            return False
        if request.method == "POST" and request.path in READ_ONLY_POSTS:
            return False
        return Editor.is_banned_ip(get_ip(request))

    def blocked_response(self, request):
        if request.path.startswith("/api/"):
            return JsonResponse({"detail": BANNED_ERROR}, status=403)

        referer_url = self.get_referer_url(request)
        if referer_url:
            # POSTのあとにGETでページを開き直させる
            response = HttpResponseRedirect(referer_url)
            response.status_code = 303
            return response

        return render(request, "subekashi/500.html", {"metatitle": "全て五百の所為です。"}, status=500)

    # トーストを表示できる、サイト内のページのURL（パスとクエリ）。外部サイトや管理サイト（トーストが無い）のRefererは使わない
    def get_referer_url(self, request):
        referer = request.META.get("HTTP_REFERER", "")
        if not referer:
            return None
        if not url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            return None
        parts = urlsplit(referer)
        if not parts.path.startswith("/") or parts.path.startswith("//") or parts.path.startswith("/admin/"):
            return None
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in TOAST_QUERY_KEYS]
        query.append(("toast", "banned"))
        return f"{parts.path}?{urlencode(query)}"
