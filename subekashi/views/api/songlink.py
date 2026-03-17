from django.db.models import Prefetch
from subekashi.models import Song, SongLink
from subekashi.lib.url import clean_url
from subekashi.lib.query_filters import make_is_lack_annotation
from ...serializer import SongLinkSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle


class SongLinkThrottle(UserRateThrottle):
    rate = '2/second'


def _make_song_queryset():
    """is_lackアノテーション付きのSongクエリセットを返す（N+1を回避）"""
    return Song.objects.annotate(
        is_lack=make_is_lack_annotation()
    ).prefetch_related('authors')


class SongLinkAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = SongLinkSerializer
    throttle_classes = [SongLinkThrottle]

    def get_queryset(self):
        qs = SongLink.objects.prefetch_related(
            Prefetch('songs', queryset=_make_song_queryset()),
        )
        url = self.request.query_params.get('url', '')
        if url:
            cleaned = clean_url(url) or url
            qs = qs.filter(url__iexact=cleaned)
        return qs

    def list(self, request, *args, **kwargs):
        result = self.get_serializer(self.get_queryset(), many=True).data
        return Response({"result": result}, headers={"Access-Control-Allow-Origin": "*"})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.get_serializer(instance).data, headers={"Access-Control-Allow-Origin": "*"})
