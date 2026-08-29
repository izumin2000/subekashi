
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from subekashi.models import Ai, Word
from subekashi.lib.lyric_tokenizer import tokenize_lyrics_with_index, REPLACEABLE_HINSHIS
from ...serializer import AiSerializer, AiWordSwapSerializer

class AiAPI(viewsets.ModelViewSet):
    queryset = Ai.objects.all()
    serializer_class = AiSerializer
    
    def create(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドCREATEは受け付けていません")
    
    def update(self, request, *args, **kwargs):
        if set(request.data.keys()) - {'score'}:
            raise serializers.ValidationError("フィールドscore以外の変更は受け付けていません")
        
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        raise serializers.ValidationError("メソッドDELETEは受け付けていません")
    
    @property
    def default_response_headers(self):
        headers = viewsets.ModelViewSet.default_response_headers.fget(self)
        headers["Access-Control-Allow-Origin"] = "*"
        return headers


class AiWordSwapThrottle(UserRateThrottle):
    rate = '30/minute'


# 単語入れ替えで作成されたAiレコードのgenetype。GPT等の他作成方式（"model"）とは区別する
SWAP_GENETYPE = 'janome'


class AiWordSwapView(APIView):
    """
    作成歌詞（Aiレコード）の単語1つを模倣単語候補に入れ替え、
    新しいAiレコード（score=0）として保存する。
    """
    throttle_classes = [AiWordSwapThrottle]

    def post(self, request, *args, **kwargs):
        serializer = AiWordSwapSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        base_id = serializer.validated_data['base_id']
        token_index = serializer.validated_data['token_index']
        candidate = serializer.validated_data['candidate']

        base = get_object_or_404(Ai, pk=base_id)
        tokens = tokenize_lyrics_with_index(base.lyrics)

        if token_index >= len(tokens):
            return Response({'detail': '指定された単語が見つかりません。'}, status=status.HTTP_400_BAD_REQUEST)

        token = tokens[token_index]
        if token['hinshi'] not in REPLACEABLE_HINSHIS:
            return Response({'detail': 'この単語は入れ替えられません。'}, status=status.HTTP_400_BAD_REQUEST)

        if not Word.is_valid_candidate(token['surface'], token['hinshi'], token['katsuyou'], candidate):
            return Response({'detail': '候補として存在しない単語です。'}, status=status.HTTP_400_BAD_REQUEST)

        new_lyrics = ''.join(
            candidate if i == token_index else t['surface']
            for i, t in enumerate(tokens)
        )

        lyrics_max_length = Ai._meta.get_field('lyrics').max_length
        if not (0 < len(new_lyrics) <= lyrics_max_length):
            return Response({'detail': '入れ替え後の歌詞が長すぎます。'}, status=status.HTTP_400_BAD_REQUEST)

        # 同じ入れ替え結果（かつ同じgenetype）が既に存在する場合は重複作成せず、既存のAiレコードを返す
        new_ai, _ = Ai.objects.get_or_create(
            lyrics=new_lyrics,
            genetype=SWAP_GENETYPE,
            defaults={'score': 0},
        )

        return Response(
            {'id': new_ai.id, 'lyrics': new_ai.lyrics},
            status=status.HTTP_201_CREATED,
            headers={"Access-Control-Allow-Origin": "*"},
        )
