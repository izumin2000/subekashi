from django.contrib import admin
from . import views
from django.urls import path, include
from rest_framework import routers

app_name = 'iniadmc'

defaultRouter = routers.DefaultRouter()
# defaultRouter.register('song', views.SongViewSet)

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.top, name = 'top'),
    # path('songs/<str:song_title>', views.song, name = 'song'),
]