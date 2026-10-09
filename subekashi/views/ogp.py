from django.core import signing
from django.http import Http404, HttpResponse
from subekashi.constants.constants import LONG_TERM_COOKIE_AGE
from subekashi.lib.ogp import load_ogp_token, render_ogp_image


# 画像はリクエストごとにメモリ上で生成し、サーバーには保存しない。
# トークンはタイトルを署名したもので、タイトルが変わるとURLも変わるため長期間キャッシュさせる
def ogp_image(request, token):
    try:
        title = load_ogp_token(token)
    except signing.BadSignature:
        raise Http404

    response = HttpResponse(render_ogp_image(title), content_type="image/png")
    response["Cache-Control"] = f"public, max-age={LONG_TERM_COOKIE_AGE}"
    return response
