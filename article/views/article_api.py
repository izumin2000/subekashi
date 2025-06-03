from article.models import Article
from rest_framework import viewsets
from article.serializer import ArticleSerializer

class ArticleAPI(viewsets.ReadOnlyModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer