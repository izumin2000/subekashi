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
            if request.GET.get("search") == "True":
                response_data = statistics
                response_data["result"] = result
                return Response(response_data)

            return Response(result)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)