from subekashi.models import Song
from subekashi.lib.search import song_search
from ...serializer import SongSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

class SongThrottle(UserRateThrottle):
    rate= '2/second'


class SongAPI(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    throttle_classes = [SongThrottle]

    def get_queryset(self):
        if self.action == 'retrieve':
            return super().get_queryset()  # 標準のクエリセットを使用

        query = dict(self.request.query_params)
        return song_search(query)

    def list(self, request, *args, **kwargs):
        result_qs, statistics = self.get_queryset()
        result = self.get_serializer(result_qs, many=True).data
        if len(statistics) == 0:
            return Response(result)
        
        response_data = statistics
        response_data["result"] = result
        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        # `song_id` に基づいて個別の `Song` を取得
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
