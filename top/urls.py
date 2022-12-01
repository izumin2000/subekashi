from . import views
from django.urls import path,include
from rest_framework import routers

defaultRouter = routers.DefaultRouter()
defaultRouter.register('song', views.SongViewSet)
defaultRouter.register('ai', views.AiViewSet)

urlpatterns = [
    path('api/',include(defaultRouter.urls)),
]