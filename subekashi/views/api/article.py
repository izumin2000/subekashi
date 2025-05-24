from subekashi.models import Article
from rest_framework import viewsets
from ...serializer import ArticleSerializer

class ArticleAPI(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer