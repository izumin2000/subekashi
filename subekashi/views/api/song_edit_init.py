from django.db.models import Prefetch
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from subekashi.models import SongLink
from subekashi.lib.song_search import song_search
from subekashi.lib.url import clean_url
from subekashi.lib.query_filters import make_is_lack_annotation
from subekashi.serializer import SongSerializer, SongLinkSerializer
from subekashi.models import Song


class SongEditInitThrottle(UserRateThrottle):
    rate = '2/second'


def _song_queryset_for_links():
    return Song.objects.annotate(
        is_lack=make_is_lack_annotation()
    ).prefetch_related('authors')


class SongEditInitView(APIView):
    throttle_classes = [SongEditInitThrottle]

    def get(self, request):
        song_id = request.query_params.get('song_id', '')
        title = request.query_params.get('title', '')
        authors = request.query_params.get('authors', '')
        urls_param = request.query_params.get('urls', '')
        fetch_imitate = request.query_params.get('fetch_imitate', '')

        # タイトル・作者の完全一致チェック
        title_author_songs = None
        if title and authors.strip():
            qs, _ = song_search({'title_exact': title, 'author_exact': authors})
            title_author_songs = list(SongSerializer(qs, many=True).data)

        # 模倣元一覧
        imitate_songs = None
        if fetch_imitate and song_id:
            qs, _ = song_search({'imitated': song_id})
            imitate_songs = list(SongSerializer(qs, many=True).data)

        # URLごとの重複チェック（入力URLの順序を保持したリスト）
        song_links = None
        if urls_param:
            cleaned_urls_str = clean_url(urls_param)
            url_list = cleaned_urls_str.split(',')
            song_links = []
            for url in url_list:
                url = url.strip()
                if not url:
                    song_links.append([])
                    continue
                qs = SongLink.objects.prefetch_related(
                    Prefetch('songs', queryset=_song_queryset_for_links())
                ).filter(url__iexact=url)
                song_links.append(list(SongLinkSerializer(qs, many=True).data))

        return Response(
            {
                'title_author_songs': title_author_songs,
                'imitate_songs': imitate_songs,
                'song_links': song_links,
            },
            headers={"Access-Control-Allow-Origin": "*"}
        )
