from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from article.models import Article
from subekashi.lib.permissions import HasAPIKey
from subekashi.serializer import NewsSerializer

NEWS_AUTHOR = "全て歌詞の所為です。"


class NewsAPIView(APIView):
    """POST -> {'article_id': 'xxx', 'title': 'ニュースの文章'} を受け取り、トップに表示するニュースを登録する（#925）"""

    # Cookieのセッションでは認証せず、X-API-Keyヘッダーだけで認可する
    authentication_classes = []
    permission_classes = [HasAPIKey]

    def post(self, request, *args, **kwargs):
        serializer = NewsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        article = Article(
            article_id=serializer.validated_data["article_id"],
            title=serializer.validated_data["title"],
            tag="news",
            author=NEWS_AUTHOR,
            post_time=timezone.now(),
        )
        # 既存の記事と同じarticle_id・HTMLに変換後のタイトルの文字数超過をエラーにする
        try:
            article.full_clean()
        except DjangoValidationError as e:
            return Response(e.message_dict, status=status.HTTP_400_BAD_REQUEST)

        # 同じarticle_idの記事が同時に登録されても上書きしないよう、INSERTのみ行う
        article.save(force_insert=True)

        return Response(
            {"article_id": article.article_id, "title": article.title},
            status=status.HTTP_201_CREATED,
        )
