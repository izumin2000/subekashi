from django.views.generic.base import RedirectView
from django.urls import path, include
from config.settings import ROOT_URL
from subekashi.views import *
from rest_framework import routers

app_name='subekashi'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', SongAPI)
defaultRouter.register('ai', AiAPI)
defaultRouter.register('ad', AdAPI)

urlpatterns = [
    path('', top, name='top'),
    path('contact/', contact, name='contact'),
    path('search/', RedirectView.as_view(url=f"{ROOT_URL}/songs/", permanent=False)),
    path('songs/', search, name='search'),
    path('songs/new/', song_new, name='song_new'),
    path('new/', RedirectView.as_view(url='/song/new/', permanent=False)),
    path('songs/<int:song_id>/', song, name='song'),
    path('songs/<int:song_id>/edit/', song_edit, name='song_edit'),
    path('songs/<int:song_id>/delete/', song_delete, name='song_delete'),
    path('channel/<str:channelName>/', channel, name='channel'),
    path('ai/', ai, name='ai'),
    path('ai/result/', ai_result, name='ai_result'),
    path('discord/', discord, name='discord'),
    path('setting/', setting, name='setting'),
    path('ad/', ad, name='ad'),
    path('ad/complete/', ad_complete, name='ad_complete'),
    path('special/', special, name='special'),
    path('robots.txt', robots, name='robots'),
    path('sitemap.xml', sitemap, name='sitemap'),
    path('favicon.ico', favicon, name='favicon'),
    path('.well-known/traffic-advice', trafficAdvice, name='traffic-advice'),
    path('api/',include(defaultRouter.urls)),
    path('api/html/song_cards', song_cards, name='song_cards'),
    path('api/html/song_guessers', song_guessers, name='song_guessers'),
    path('api/html/toast', toast, name='toast'),
]