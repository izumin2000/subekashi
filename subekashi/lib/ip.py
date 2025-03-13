from subekashi.lib.security import encrypt

def get_ip(request, is_encrypted=True):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = forwarded_addresses.split(',')[0] if forwarded_addresses else request.META.get('REMOTE_ADDR')
    
    if is_encrypted:
        return encrypt(ip_address)
    
    return ip_address