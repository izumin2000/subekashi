from rest_framework import throttling
from subekashi.lib.ip import get_client_ip


# DRFの既定のget_identはX-Forwarded-Forの全体を識別子にするため、クライアントが値を変えるだけで制限を回避できる。
# django_ratelimitと同じくX-Real-IP（無ければREMOTE_ADDR）で数える（#1192）
class ClientIPThrottleMixin:
    def get_ident(self, request):
        return get_client_ip(request)


class AnonRateThrottle(ClientIPThrottleMixin, throttling.AnonRateThrottle):
    pass


class UserRateThrottle(ClientIPThrottleMixin, throttling.UserRateThrottle):
    pass
