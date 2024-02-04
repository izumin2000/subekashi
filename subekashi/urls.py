from django.contrib import admin
from . import views
from django.urls import path, include
from rest_framework import routers

app_name='subekashi'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', views.SongViewSet)
defaultRouter.register('ai', views.AiViewSet)

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.top, name='top'),
    path('new', views.new, name='new'),
    path('delete', views.delete, name='delete'),
    path('songs/<int:songId>', views.song, name='song'),
    path('channel/<str:channelName>', views.channel, name='channel'),
    path('search', views.search, name='search'),
    path('ai', views.ai, name='ai'),
    path('setting', views.setting, name='setting'),
    path('research', views.research, name='research'),
    path('error', views.error, name='error'),
    path('dev', views.dev, name='dev'),
    path('github', views.github, name='github'),
    path('robots.txt', views.robots, name='robots'),
    path('sitemap.xml', views.sitemap, name='sitemap'),
    path('apple-touch-icon.png', views.appleicon, name='apple-touch-icon'),
    path('api/',include(defaultRouter.urls)),
    path('api/clean', views.clean, name='clean'),
    path('onigiri', views.onigiri, name='onigiri'),
]