from subekashi.models import Song
from subekashi.lib.search import song_search
from ..serializer import SongSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response


class SongAPI(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    cached_data = None

    def get_queryset(self):
        if self.action == 'retrieve':
            return super().get_queryset()  # 標準のクエリセットを使用

        if self.cached_data is None:
            query = dict(self.request.query_params)
            result = song_search(query)

            # エラーが発生している場合、エラー内容をレスポンスとして返す
            if isinstance(result, dict) and "error" in result:
                raise ValueError(result["error"])

            self.cached_data = result
        return self.cached_data

    def list(self, request, *args, **kwargs):
        try:
            result_qs, statistics = self.get_queryset()
            result = self.get_serializer(result_qs, many=True).data
            if len(statistics) == 0:
                return Response(result)
            
            response_data = statistics
            response_data["result"] = result
            return Response(response_data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, *args, **kwargs):
        # `song_id` に基づいて個別の `Song` を取得
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
