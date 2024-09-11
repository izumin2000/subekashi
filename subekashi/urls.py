from django.contrib import admin
from django.urls import path, include
from . import views
from rest_framework import routers

app_name='subekashi'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', views.SongViewSet)
defaultRouter.register('ai', views.AiViewSet)
defaultRouter.register('ad', views.AdViewSet)

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
    path('ad', views.ad, name='ad'),
    path('ad/post', views.adpost, name='adpost'),
    path('research', views.research, name='research'),
    path('special', views.special, name='special'),
    path('robots.txt', views.robots, name='robots'),
    path('sitemap.xml', views.sitemap, name='sitemap'),
    path('favicon.ico', views.favicon, name='favicon'),
    path('.well-known/traffic-advice', views.trafficAdvice, name='traffic-advice'),
    path('api/',include(defaultRouter.urls)),
    path('api/clean', views.clean, name='clean'),
]