from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import UserRateThrottle
from subekashi.models import Word


class WordCandidatesThrottle(UserRateThrottle):
    rate = '5/second'


class WordCandidatesView(APIView):
    """
    指定した単語・品詞と同じ品詞の模倣単語候補を最大10件返す。
    """
    throttle_classes = [WordCandidatesThrottle]

    def get(self, request, *args, **kwargs):
        word = request.query_params.get('word', '')
        hinshi = request.query_params.get('hinshi', '')
        # katsuyouは副詞・連体詞では空文字列が正当な値のため、
        # word・hinshiのように未指定チェックの対象にはしない
        katsuyou = request.query_params.get('katsuyou', '')
        if not word or not hinshi:
            return Response({'detail': 'wordとhinshiは必須です。'}, status=status.HTTP_400_BAD_REQUEST)

        candidates = Word.get_candidates(word, hinshi, katsuyou, limit=10)
        return Response(
            {'candidates': candidates},
            headers={"Access-Control-Allow-Origin": "*"},
        )
