import ipaddress
from subekashi.lib.security import encrypt

# 編集者の識別・お問い合わせのIP・BANの判定に使うIP。X-Forwarded-Forはクライアントが自由に付けられ、
# 先頭を使うと他人のIPを名乗れるため、レート制限と同じくX-Real-IP（無ければREMOTE_ADDR）を使う（#1189）
def get_ip(request, raw=False):
    ip_address = get_client_ip(request)
    return ip_address if raw else encrypt(ip_address)

# PythonAnywhereではREMOTE_ADDRがロードバランサーのIPになるため、ロードバランサーが付けるX-Real-IPを使う（#1188）。
# ロードバランサーがX-Real-IPを付け直す前提のため、別の環境に移す場合は見直す
# （クライアントが送ったX-Real-IPがそのまま届くと、値を変えるだけでレート制限を回避できる）。
# IPでない値はdjango_ratelimitが解析できず500になるため、REMOTE_ADDRを使う
def get_client_ip(request):
    real_ip = request.META.get('HTTP_X_REAL_IP', '')
    try:
        ipaddress.ip_address(real_ip)
    except ValueError:
        return request.META['REMOTE_ADDR']
    return real_ip
