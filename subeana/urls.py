from django.contrib import admin
from . import views
from django.urls import path,include
from rest_framework import routers

app_name = 'subeana'

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', views.SongViewSet)

urlpatterns = [
    path('admin', admin.site.urls),
    path('', views.top, name = 'top'),
    path('new', views.new, name = 'new'),
    path('api/',include(defaultRouter.urls)),
]