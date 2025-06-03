from django.urls import path
from article.views import *

app_name='article'

urlpatterns = [
    path('', articles, name='articles'),
    path('<str:id>/', default_article, name='default_article'),
]