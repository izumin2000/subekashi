import unicodedata


# 濁点・半濁点の正規化
class NormalizePostDataMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST":
            if request.POST._mutable is False:
                request.POST._mutable = True

            for key in request.POST.keys():
                values = request.POST.getlist(key)
                normalized_values = [
                    unicodedata.normalize('NFC', v) if isinstance(v, str) else v
                    for v in values
                ]
                
                if len(normalized_values) == 1:
                    request.POST[key] = normalized_values[0]
                else:
                    request.POST.setlist(key, normalized_values)

            request.POST._mutable = False

        response = self.get_response(request)
        return response
