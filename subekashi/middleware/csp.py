import secrets

# Google Analyticsの読み込み元・送信先（Googleシグナル利用時を含む）
GOOGLE_ANALYTICS_SOURCES = [
    "https://*.google-analytics.com",
    "https://*.analytics.google.com",
    "https://*.googletagmanager.com",
    "https://*.g.doubleclick.net",
    "https://*.google.com",
    "https://*.google.co.jp",
]

# インラインスクリプトはリクエストごとのnonceを付与したものだけを許可する。
# インラインのイベントハンドラ属性（onclick等）は許可していないため、JSからaddEventListenerで登録すること
CSP_DIRECTIVES = {
    "default-src": ["'self'"],
    "script-src": [
        "'self'",
        "https://www.googletagmanager.com",     # Google Analytics
        "https://www.youtube.com",              # YouTube IFrame Player API（トップの宣伝枠）
        "https://cdn.jsdelivr.net",             # Chart.js（統計）
        "https://platform.twitter.com",         # ポストの埋め込み（リリリク記事）
    ],
    # style属性やJSで生成する<style>を使用している箇所があるため'unsafe-inline'を許可する
    "style-src": [
        "'self'",
        "'unsafe-inline'",
        "https://use.fontawesome.com",
        "https://themes.googleusercontent.com",     # Googleドキュメントから書き出した記事（peper記事）のフォント
    ],
    "font-src": ["'self'", "https://use.fontawesome.com", "https://fonts.gstatic.com"],
    "img-src": ["'self'", "data:", *GOOGLE_ANALYTICS_SOURCES],
    "connect-src": [
        "'self'",
        "https://global-header.imicom.workers.dev",     # 界隈グローバルヘッダー
        "https://discord.com",                          # Discordサーバー情報（discord記事）
        *GOOGLE_ANALYTICS_SOURCES,
    ],
    "frame-src": [
        "https://www.youtube-nocookie.com",
        "https://www.youtube.com",
        "https://platform.twitter.com",
    ],
    "object-src": ["'none'"],
    "base-uri": ["'self'"],
    "form-action": ["'self'"],
    "frame-ancestors": ["'none'"],
}


def build_csp(nonce):
    directives = []
    for directive, sources in CSP_DIRECTIVES.items():
        if directive == "script-src":
            sources = [*sources, f"'nonce-{nonce}'"]
        directives.append(f"{directive} {' '.join(sources)}")
    return "; ".join(directives)


class ContentSecurityPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(16)
        response = self.get_response(request)

        if "Content-Security-Policy" in response:
            return response

        if response.get("Content-Type", "").startswith("text/html"):
            response["Content-Security-Policy"] = build_csp(request.csp_nonce)

        return response
