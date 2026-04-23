from django.urls import path
from article.views import *

app_name='article'

urlpatterns = [
    path('', ArticlesView.as_view(), name='articles'),
    path('lilyriku/', lilyrikuView.as_view(), name='lilyriku'),
    path('anniversary6/', Anniversary6View.as_view(), name='anniversary6'),
    path('<str:id>/', DefaultArticleView.as_view(), name='default_article'),
]
