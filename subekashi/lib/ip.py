

def get_ip(request):
    forwarded_addresses = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_addresses:
        ip_address = forwarded_addresses.split(',')[0]
    else:
        ip_address = request.META.get('REMOTE_ADDR')
    return ip_address