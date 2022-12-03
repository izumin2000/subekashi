from django.contrib import admin
from . import views
from django.urls import path,include
from rest_framework import routers


app_name = 'subekashi'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', views.SongViewSet)
defaultRouter.register('ai', views.AiViewSet)

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.top, name = 'top'),
    path('new', views.new, name = 'new'),
    path('make', views.make, name = 'make'),
    path('edit', views.edit, name = 'edit'),
    path('songs/<int:song_id>', views.song, name = 'song'),
    path('channel/<str:channel_name>', views.channel, name = 'channel'),
    path('search', views.search, name = 'search'),
    path('wrong/<int:song_id>', views.wrong, name = 'wrong'),
    path('error', views.error, name = 'error'),
    path('dev', views.dev, name = 'dev'),
    path('api/',include(defaultRouter.urls)),
    path('login/', views.Login, name='login'),
    path('logout/', views.Logout.as_view(), name='logout'),
    path('oauth/', include('social_django.urls', namespace='social')),
]