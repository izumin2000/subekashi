import math
from rest_framework.pagination import BasePagination
from rest_framework.response import Response


# 公開API（#1243）のページ分割。曲のAPI（song_search）と同じく、page・sizeで取得する範囲を指定し、件数とページ数を返す
class OpenDataPagination(BasePagination):
    default_size = 50
    # 1度に大量のデータを読み込まないよう、上限を超えるsizeは上限にする
    max_size = 1000

    def paginate_queryset(self, queryset, request, view=None):
        self.count = queryset.count()
        self.page = self._get_positive_int(request, "page", 1)
        self.size = min(self._get_positive_int(request, "size", self.default_size), self.max_size)
        start = (self.page - 1) * self.size
        # 範囲外のページは、大きなOFFSETのクエリを実行せずに空にする
        if start >= self.count:
            return []
        return list(queryset[start:start + self.size])

    def get_paginated_response(self, data):
        return Response({
            "count": self.count,
            "page": self.page,
            "size": self.size,
            "max_page": math.ceil(self.count / self.size),
            "result": data,
        })

    # ブラウザで表示するAPIの画面が、一覧かどうかの判定と結果の表示に使う
    def get_results(self, data):
        return data["result"]

    # 曲のAPIと同じく、数値でない値・1未満の値は既定値にする
    def _get_positive_int(self, request, name, default):
        try:
            value = int(request.query_params.get(name, default))
        except (TypeError, ValueError):
            return default
        return value if value >= 1 else default
