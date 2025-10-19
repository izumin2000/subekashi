from subekashi.lib.security import encrypt

def get_ip(request):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    ip_address = forwarded_addresses.split(',')[0] if forwarded_addresses else request.META.get('REMOTE_ADDR')
    return encrypt(ip_address)