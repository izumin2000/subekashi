from subekashi.models import SongLink
from subekashi.lib.url import clean_url
from ...serializer import SongLinkSerializer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle


class SongLinkThrottle(UserRateThrottle):
    rate = '2/second'


class SongLinkAPI(viewsets.ReadOnlyModelViewSet):
    serializer_class = SongLinkSerializer
    throttle_classes = [SongLinkThrottle]

    def get_queryset(self):
        qs = (
            SongLink.objects
            .filter(allow_dup=False)
            .select_related('song')
            .prefetch_related('song__authors')
        )
        url = self.request.query_params.get('url', '')
        if url:
            cleaned = clean_url(url) or url
            qs = qs.filter(url__icontains=cleaned)
        return qs

    def list(self, request, *args, **kwargs):
        result = self.get_serializer(self.get_queryset(), many=True).data
        return Response({"result": result}, headers={"Access-Control-Allow-Origin": "*"})

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.get_serializer(instance).data, headers={"Access-Control-Allow-Origin": "*"})
