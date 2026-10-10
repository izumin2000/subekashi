import hashlib
import os
from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.utils.http import parse_etags
from django_ratelimit.core import is_ratelimited
from subekashi.constants.constants import LONG_TERM_COOKIE_AGE, SHORT_TERM_COOKIE_AGE
from subekashi.lib.ogp import OGP_VERSION, load_ogp_token, render_ogp_image

STATIC_OGP_IMAGE_PATH = os.path.join(settings.BASE_DIR, "subekashi/static/subekashi/image/ogp.png")
OGP_CACHE_TIMEOUT = 24 * 60 * 60


# PythonAnywhereではREMOTE_ADDRがロードバランサーのIPになるため、ロードバランサーが付けるX-Real-IPで制限する。
# ロードバランサーがX-Real-IPを付け直す前提のため、別の環境に移す場合は見直す
# （クライアントが送ったX-Real-IPがそのまま届くと、値を変えるだけで制限を回避できる）
def get_client_ip(group, request):
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR", "")


def set_image_headers(response, image_etag):
    response["ETag"] = image_etag
    response["Cache-Control"] = f"public, max-age={LONG_TERM_COOKIE_AGE}"
    return response


# 画像はリクエストごとにメモリ上で生成し、ファイルには保存しない。
# トークンはタイトルを署名したもので、タイトルが変わるとURLも変わるため長期間キャッシュさせる
def ogp_image(request, token):
    try:
        title = load_ogp_token(token)
    except signing.BadSignature:
        raise Http404
    if not title:
        raise Http404

    digest = hashlib.sha256(f"{OGP_VERSION}:{token}".encode()).hexdigest()
    image_etag = f'"{digest[:32]}"'
    if image_etag in parse_etags(request.headers.get("If-None-Match", "")):
        return set_image_headers(HttpResponseNotModified(), image_etag)

    cache_key = f"ogp_image:{digest}"
    image = cache.get(cache_key)
    if image is None:
        # 新しく描画するときだけ回数を数える。SNSのクローラーに失敗をキャッシュされないよう、429はキャッシュさせない
        if is_ratelimited(request, group="ogp_image", key=get_client_ip, rate="5/s", increment=True):
            response = HttpResponse("Too Many Requests", status=429, content_type="text/plain")
            response["Retry-After"] = "1"
            response["Cache-Control"] = "no-store"
            return response

        try:
            image = render_ogp_image(title)
        except OSError:
            # フォントを読み込めない環境（FreeTypeがwoff2に対応していない等）では、共通の画像を短時間だけキャッシュさせて返す
            with open(STATIC_OGP_IMAGE_PATH, "rb") as f:
                response = HttpResponse(f.read(), content_type="image/png")
            response["Cache-Control"] = f"public, max-age={SHORT_TERM_COOKIE_AGE}"
            return response
        cache.set(cache_key, image, OGP_CACHE_TIMEOUT)

    return set_image_headers(HttpResponse(image, content_type="image/png"), image_etag)
