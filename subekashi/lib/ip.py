from subekashi.lib.security import encrypt

def get_ip(request, raw=False):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = forwarded_addresses.split(',')[0] if forwarded_addresses else request.META.get('REMOTE_ADDR')
    return ip_address if raw else encrypt(ip_address)