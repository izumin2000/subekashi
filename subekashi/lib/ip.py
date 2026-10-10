import ipaddress
import logging
from subekashi.lib.security import encrypt

logger = logging.getLogger(__name__)

def get_ip(request, raw=False):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = forwarded_addresses.split(',')[0] if forwarded_addresses else request.META.get('REMOTE_ADDR')
    return ip_address if raw else encrypt(ip_address)

# get_ipをX-Real-IPに切り替えたときに編集者が変わるリクエストの件数を確認するため、IPを含めずに記録する（#1189）
def log_forwarded_ip_mismatch(request):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    real_ip = request.META.get('HTTP_X_REAL_IP')
    if not forwarded_addresses or not real_ip:
        return

    forwarded_list = forwarded_addresses.split(',')
    if forwarded_list[0].strip() != real_ip.strip():
        logger.warning(
            "X-Forwarded-For の先頭と X-Real-IP が一致しません（%s %r、X-Forwarded-For の IP の数: %d）",
            request.method, request.path, len(forwarded_list),
        )

def describe_ip(value):
    if not value:
        return 'なし'
    try:
        is_global = ipaddress.ip_address(value).is_global
    except ValueError:
        return 'IPでない'
    return 'グローバル' if is_global else 'グローバルでない'

# 本番でREMOTE_ADDRがロードバランサーのIPになり、X-Real-IPがロードバランサーに付け直されているかを確認するため、
# 確認用のパスへのリクエストだけ、IPを含めずに記録する（#1191）。確認が済んだら削除する
def log_client_ip_check(request):
    if not request.path.startswith('/x-real-ip-check'):
        return

    remote_addr = request.META.get('REMOTE_ADDR', '')
    real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    forwarded_list = [address.strip() for address in forwarded_addresses.split(',')] if forwarded_addresses else []
    logger.warning(
        "IP の確認（%s %r、REMOTE_ADDR: %s、X-Real-IP: %s、REMOTE_ADDR と X-Real-IP が一致: %s、"
        "X-Forwarded-For の IP の数: %d、X-Real-IP と X-Forwarded-For の先頭が一致: %s、末尾が一致: %s）",
        request.method, request.path, describe_ip(remote_addr), describe_ip(real_ip),
        bool(real_ip) and remote_addr == real_ip, len(forwarded_list),
        bool(forwarded_list) and forwarded_list[0] == real_ip,
        bool(forwarded_list) and forwarded_list[-1] == real_ip,
    )

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
