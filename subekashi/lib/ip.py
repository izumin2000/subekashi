from subekashi.lib.security import encrypt

# TODO encryptを削除・全プロジェクトでis_encrypted引数を削除
def get_ip(request, is_encrypted=True):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = forwarded_addresses.split(',')[0] if forwarded_addresses else request.META.get('REMOTE_ADDR')
    
    if is_encrypted or (ip_address != "127.0.0.1"):
        return encrypt(ip_address)
    
    return ip_address