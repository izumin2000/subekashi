from subekashi.models import Song
from subekashi.lib.song_filter import song_filter
from ...serializer import SongSerializer
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.exceptions import ValidationError

class SongThrottle(UserRateThrottle):
    rate= '2/second'


class SongAPI(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer
    throttle_classes = [SongThrottle]

    def get_queryset(self):
        if self.action == 'retrieve':
            return super().get_queryset()

        query = dict(self.request.query_params)
        return song_filter(query)

    def list(self, request, *args, **kwargs):
        try:
            result_qs, statistics = self.get_queryset()
            result = self.get_serializer(result_qs, many=True).data
            if len(statistics) == 0:
                return Response(result, headers={"Access-Control-Allow-Origin": "*"})

            response_data = statistics
            response_data["result"] = result
            return Response(response_data, headers={"Access-Control-Allow-Origin": "*"})
        except ValidationError as e:
            # バリデーションエラーを {"error": エラー内容} の形式で返す
            error_detail = e.detail
            if isinstance(error_detail, dict) and "error" in error_detail:
                return Response(error_detail, status=status.HTTP_400_BAD_REQUEST, headers={"Access-Control-Allow-Origin": "*"})
            return Response({"error": str(error_detail)}, status=status.HTTP_400_BAD_REQUEST, headers={"Access-Control-Allow-Origin": "*"})

    def retrieve(self, request, *args, **kwargs):
        # `song_id` に基づいて個別の `Song` を取得
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data, headers={"Access-Control-Allow-Origin": "*"})
