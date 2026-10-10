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
