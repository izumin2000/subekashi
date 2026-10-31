from django.http import QueryDict
from subekashi.models import Song
from subekashi.converters import parse_sqlite_id
from subekashi.lib.song_search import song_search
from subekashi.lib.permissions import HasIssuedAPIKey
from ...serializer import SongSerializer
from rest_framework import viewsets, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response
from subekashi.lib.throttling import UserRateThrottle
from subekashi.views.api.song_write import (
    SongNewAPIView,
    SongEditAPIView,
    SongDeleteAPIView,
    NOT_FOUND_ERROR,
    build_delete_post_data,
    build_edit_post_data,
    build_error_response,
    build_new_post_data,
    get_created_song_id,
    get_request_data,
    run_view,
)

class SongThrottle(UserRateThrottle):
    rate= '2/second'


# 曲の取得（GET）は誰でも、登録（POST）・変更（PUT・PATCH）・削除（DELETE）は管理サイトで発行したAPIキー（X-API-Keyヘッダー）が必要（#973）
class SongAPI(viewsets.ReadOnlyModelViewSet):
    # SongSerializerがプレラの名前を返すため、曲ごとにプレラを取得しないようselect_relatedする（#1064）
    queryset = Song.objects.select_related('prush').prefetch_related('links')
    serializer_class = SongSerializer
    throttle_classes = [SongThrottle]
    # Cookieのセッションでは認証せず、APIキーだけで認可する。管理サイトにログインしていてもCSRFトークンを求められない
    authentication_classes = []

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [HasIssuedAPIKey()]
        return super().get_permissions()

    def get_queryset(self):
        if self.action == 'retrieve':
            return super().get_queryset()

        query = dict(self.request.query_params)
        return song_search(query)

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

    def create(self, request, *args, **kwargs):
        post_data = build_new_post_data(get_request_data(request))
        view, response = run_view(SongNewAPIView, request, post_data)
        error_response = build_error_response(view, response)
        if error_response:
            return error_response

        song = self.queryset.get(pk=get_created_song_id(response))
        return Response(self.get_serializer(song).data, status=status.HTTP_201_CREATED)

    # PUTもPATCHも、指定しなかった項目は今の曲の値のままにする
    def update(self, request, *args, **kwargs):
        song_id = self.get_song_id(kwargs)
        data = get_request_data(request)
        # 曲が無い・削除されているときは、フォームを読む前にビューが404・410を返す
        song = Song.get_or_none(song_id)
        post_data = QueryDict() if song is None else build_edit_post_data(data, song)
        view, response = run_view(SongEditAPIView, request, post_data, song_id=song_id)
        error_response = build_error_response(view, response)
        if error_response:
            return error_response

        return Response(self.get_serializer(self.queryset.get(pk=song_id)).data)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        song_id = self.get_song_id(kwargs)
        post_data = build_delete_post_data(get_request_data(request))
        view, response = run_view(SongDeleteAPIView, request, post_data, song_id=song_id)
        error_response = build_error_response(view, response)
        if error_response:
            return error_response

        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_song_id(self, kwargs):
        song_id = parse_sqlite_id(kwargs['pk'])
        if song_id is None:
            raise NotFound({"error": NOT_FOUND_ERROR})
        return song_id
