from django.conf import settings
from django.core import signing
from django.http import Http404, HttpResponse
from django.shortcuts import redirect
from django.templatetags.static import static
from django_ratelimit.decorators import ratelimit
from subekashi.constants.constants import LONG_TERM_COOKIE_AGE
from subekashi.lib.ogp import load_ogp_token, render_ogp_image


# PythonAnywhereではREMOTE_ADDRがロードバランサーのIPになるため、ロードバランサーが付けるX-Real-IPで制限する
def get_client_ip(group, request):
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")


# 画像はリクエストごとにメモリ上で生成し、サーバーには保存しない。
# トークンはタイトルを署名したもので、タイトルが変わるとURLも変わるため長期間キャッシュさせる。
# SNSのクローラーは同じIPからまとめて取りに来ることがあるため、song_cardsより緩く制限する
@ratelimit(key=get_client_ip, rate='5/s', method=['GET', 'HEAD'], block=True)
def ogp_image(request, token):
    try:
        title = load_ogp_token(token)
    except signing.BadSignature:
        raise Http404

    try:
        image = render_ogp_image(title)
    except OSError:
        # フォントを読み込めない環境（FreeTypeがwoff2に対応していない等）では、共通の画像を返す
        return redirect(f"{settings.ROOT_URL}{static('subekashi/image/ogp.png')}")

    response = HttpResponse(image, content_type="image/png")
    response["Cache-Control"] = f"public, max-age={LONG_TERM_COOKIE_AGE}"
    return response
