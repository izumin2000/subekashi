from subekashi.models import Song
from rest_framework import viewsets
from ..serializer import SongSerializer


class SongAPI(viewsets.ReadOnlyModelViewSet):
    queryset = Song.objects.all()
    serializer_class = SongSerializer